import inspect
import weakref
import wrapt
from .exceptions import *
from collections import UserDict


class NoOverwriteDict(UserDict):
    def __setitem__(self, key, value):
        if key in self:
            raise DuplicateServiceError(key)
        super(NoOverwriteDict, self).__setitem__(key, value)


class ServicesContainer:
    auto_wire = True

    def __init__(self):
        self._services = NoOverwriteDict()
        self._services_instances = NoOverwriteDict()
        self.builder = ServiceBuilder(weakref.proxy(self))

    def __getitem__(self, item):
        try:
            return self._services_instances[item]
        except KeyError:
            try:
                service = self._services[item]
            except KeyError:
                raise UndefinedServiceError(item)
            else:
                if service.auto_wire:
                    instance = self.builder.build(service.obj)
                else:
                    instance = service.obj()

                self._services_instances[item] = instance
                return instance

    def __setitem__(self, key, value):
        if key in self._services_instances:
            raise DuplicateServiceError(key)
        self._services_instances[key] = value

    def register(self, service=None, name=None, auto_wire=True):
        def _register(obj):
            if inspect.isclass(obj):
                service = Service(obj, auto_wire=auto_wire)
                self._services[obj] = service
                if name:
                    self._services[name] = service
            else:
                self._services_instances[name or obj.__name__] = obj

            return obj

        if service:
            return _register(service)

        return _register

    def inject(self, func=None):
        @wrapt.decorator
        def _inject(wrapped, instance, args, kwargs):
            return self.builder.build(wrapped, args, kwargs)

        if func:
            return _inject(func)

        return _inject


class Service:
    def __init__(self, obj, auto_wire):
        self.obj = obj
        self.auto_wire = auto_wire


class ServiceBuilder:
    def __init__(self, container):
        self._container = container

    def build(self, obj, args=None, kwargs=None, use_name=True):
        args = args if args is not None else tuple()
        kwargs = kwargs if kwargs is not None else {}
        f = obj.__init__ if inspect.isclass(obj) else obj

        new_args, new_kwargs = self._inject_services(f, args, kwargs,
                                                     use_name=use_name)

        try:
            return obj(*new_args, **new_kwargs)
        except Exception as e:
            raise ServiceInstantiationError(e)

    def _inject_services(self, f, args, kwargs, use_name):
        signature = inspect.signature(f)
        new_parameters = []

        for name, parameter in signature.parameters.items():
            if name == 'self':
                continue

            try:
                if parameter.annotation != parameter.empty:
                    service = parameter.annotation
                elif use_name:
                    service = name
                else:
                    service = None

                if service:
                    parameter = parameter.replace(
                        default=self._container[service]
                    )
            except UndefinedServiceError:
                pass
            finally:
                new_parameters.append(parameter)

        signature = signature.replace(parameters=new_parameters)
        bound_arguments = signature.bind_partial(*args, **kwargs)
        bound_arguments.apply_defaults()

        return bound_arguments.args, bound_arguments.kwargs
