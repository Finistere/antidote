import inspect
import weakref
import wrapt
import sys
from .exceptions import *
from .util import to_snake_case, to_CamelCase
from collections import UserDict

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap


PY3 = sys.version_info[0] >= 3


class ServicesDict(UserDict):
    def __setitem__(self, key, value):
        if key in self:
            raise DuplicateServiceError(key)
        super(ServicesDict, self).__setitem__(key, value)


class ServiceManager:
    def __init__(self):
        self.container = Container()
        self.builder = Builder(self.container)

    def _create_service(self, factory, **kwargs):
        return Service(builder=weakref.proxy(self.builder), factory=factory,
                       **kwargs)

    def build(self, cls, *args, **kwargs):
        return self.builder.build(cls, args=args, kwargs=kwargs)

    def register(self, service=None, id=None, singleton=None):
        if service and not inspect.isclass(service) and not id:
            raise ValueError('name cannot be None')

        def _register(obj):
            if inspect.isclass(obj):
                self.container.register(
                    service=self._create_service(obj, singleton=singleton),
                    id=obj,
                    user_id=id
                )
            else:
                self.container[id] = obj

            return obj

        if service:
            return _register(service)

        return _register

    if PY3:
        def provider(self, service=None, id=None):
            def _provider(obj):
                if inspect.isclass(obj):
                    obj = obj()
                    service_id = obj.__call__.__annotations__['return']
                else:
                    service_id = obj.__annotations__['return']

                self.container.register(
                    service=self._create_service(obj, singleton=False),
                    id=service_id,
                    user_id=id
                )

                return obj

            if service:
                return _provider(service)

            return _provider
    else:
        def provider(self, service=None, id=None):
            def _provider(obj):
                service_id = obj.__name__
                if inspect.isclass(obj):
                    obj = obj()

                self.container.register(
                    service=self._create_service(obj, singleton=False),
                    id=service_id,
                    user_id=id
                )

                return obj

            if service:
                return _provider(service)

            return _provider

    def inject(self, func=None):
        @wrapt.decorator
        def _inject(wrapped, instance, args, kwargs):
            return self.builder.build(wrapped, args, kwargs)

        if func:
            return _inject(func)

        return _inject


class Builder:
    def __init__(self, container):
        self._container = container

    def build(self, obj, args=None, kwargs=None):
        new_args, new_kwargs = self._inject_services(obj,
                                                     args=args or tuple(),
                                                     kwargs=kwargs or dict())

        try:
            return obj(*new_args, **new_kwargs)
        except Exception as e:
            raise ServiceInstantiationError(e)

    if PY3:
        def _inject_services(self, obj, args, kwargs):
            has_self_arg = False
            if inspect.isclass(obj):
                obj = obj.__init__
                has_self_arg = True

            signature = inspect.signature(obj)
            new_parameters = []

            for i, (name, parameter) in enumerate(signature.parameters.items()):
                if has_self_arg and i == 0:
                    continue

                try:
                    if parameter.annotation != parameter.empty:
                        parameter = parameter.replace(
                            default=self._container[parameter.annotation]
                        )
                except UndefinedServiceError:
                    pass
                finally:
                    new_parameters.append(parameter)

            signature = signature.replace(parameters=new_parameters)
            bound_arguments = signature.bind_partial(*args, **kwargs)
            bound_arguments.apply_defaults()

            return bound_arguments.args, bound_arguments.kwargs
    else:
        def _inject_services(self, obj, args, kwargs):
            has_self_arg = False
            if inspect.isclass(obj):
                obj = obj.__init__
                has_self_arg = True
            arg_spec = inspect.getargspec(obj)
            kwargs = kwargs.copy()

            for i, name in enumerate(arg_spec.args[len(args):]):
                if has_self_arg and not len(args) and i == 0:
                    continue

                if name not in kwargs:
                    try:
                        kwargs[name] = self._container[name]
                    except UndefinedServiceError:
                        pass

            return args, kwargs


class Container:
    def __init__(self):
        self._services_by_user_id = ServicesDict()
        self._services_by_id = ServicesDict()

        self._services = ChainMap(
            self._services_by_user_id,
            self._services_by_id,
        )
        self._services_instances = {}

    def __getitem__(self, item):
        try:
            return self._services_instances[item]
        except KeyError:
            try:
                service = self._services[item]
            except KeyError:
                raise UndefinedServiceError(item)
            else:
                instance = service.instantiate()
                if service.singleton:
                    self._services_instances[item] = instance
                return instance

    def __setitem__(self, key, value):
        self._services_instances[key] = value

    if PY3:
        def register(self, service, id, user_id=None):
            self._services_by_id[id] = service

            if user_id:
                self._services_by_user_id[user_id] = service
    else:
        def register(self, service, id, user_id=None):
            id = str(id)
            for key in {id, to_CamelCase(id), to_snake_case(id)}:
                self._services_by_id[key] = service

            if user_id:
                self._services_by_user_id[user_id] = service


class Service:
    __slots__ = ('factory', '_builder', 'singleton')

    def __init__(self, builder, factory, singleton=None):
        self._builder = builder
        self.factory = factory
        self.singleton = singleton if singleton is None else True

    def instantiate(self, *args, **kwargs):
        try:
            return self._builder.build(self.factory, args=args,
                                       kwargs=kwargs)
        except Exception as e:
            raise ServiceInstantiationError(e)
