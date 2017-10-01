import inspect
import wrapt
import sys
from itertools import islice
from .exceptions import *

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap


PY3 = sys.version_info[0] >= 3


class ServiceManager:
    auto_wire = True

    def __init__(self):
        self.container = ServiceContainer()
        self.builder = Builder(self.container)

    def register(self, service=None, id=None, mapping=None, singleton=False,
                 auto_wire=None):
        auto_wire = self.auto_wire if auto_wire is None else auto_wire
        if service and not inspect.isclass(service) and not id:
            raise ValueError('name cannot be None')

        def _register(obj):
            if inspect.isclass(obj):
                if auto_wire and hasattr(obj, '__init__'):
                    obj.__init__ = self.inject(obj.__init__, mapping=mapping)
                self.container.register(factory=obj, singleton=singleton,
                                        id=id)
            else:
                self.container[id] = obj

            return obj

        return service and _register(service) or _register

    if PY3:
        def provider(self, service=None, returns=None, id=None, mapping=None,
                     auto_wire=True):
            auto_wire = self.auto_wire if auto_wire is None else auto_wire

            def _provider(obj):
                if inspect.isclass(obj):
                    if auto_wire:
                        obj.__call__ = self.inject(obj.__call__,
                                                   mapping=mapping)
                        obj.__init__ = self.inject(obj.__init__,
                                                   mapping=mapping)
                    service_id = obj.__call__.__annotations__['return']
                    obj = obj()
                else:
                    if auto_wire:
                        obj = self.inject(obj, mapping=mapping)
                    service_id = obj.__annotations__['return']

                self.container.register(factory=obj, singleton=False,
                                        type=returns or service_id, id=id)
                return obj

            return service and _provider(service) or _provider
    else:
        def provider(self, service=None, returns=None, id=None, mapping=None,
                     auto_wire=True):
            if returns is None:
                raise ValueError('With Python 2 the providers output must be '
                                 'explicitly specified')

            def _provider(obj):
                if inspect.isclass(obj):
                    if auto_wire:
                        obj.__call__ = self.inject(obj.__call__,
                                                   mapping=mapping)
                        obj.__init__ = self.inject(obj.__init__,
                                                   mapping=mapping)
                    obj = obj()
                elif auto_wire:
                        obj = self.inject(obj, mapping=mapping)

                self.container.register(factory=obj, type=returns,
                                        singleton=False, id=id)
                return obj

            return service and _provider(service) or _provider

    def inject(self, func=None, mapping=None):
        @wrapt.decorator
        def _inject(wrapped, instance, args, kwargs):
            return self.builder.call(wrapped, mapping=mapping, args=args,
                                     kwargs=kwargs)

        return func and _inject(func) or _inject

    def attrib(self, service=None, **kwargs):
        import attr

        def attrib_factory(instance):
            if service is None:
                cls = instance.__class__
                for name, value in cls.__dict__.items():
                    # Dirty way to find the attrib annotation.
                    # Maybe attr will eventually provide the annotation ?
                    if isinstance(value, attr.Attribute) \
                            and isinstance(value.default, attr.Factory)\
                            and value.default.factory == attrib_factory:
                        return self.container[cls.__annotations__[name]]

            return self.container[service]

        return attr.ib(default=attr.Factory(attrib_factory, takes_self=True),
                       **kwargs)


class Builder:
    def __init__(self, container):
        self._container = container

    def build(self, cls, mapping=None, args=None, kwargs=None):
        new_args, new_kwargs = self._inject_services(cls.__init__,
                                                     skip_self=True,
                                                     mapping=mapping or dict(),
                                                     args=args or tuple(),
                                                     kwargs=kwargs or dict())

        return cls(*new_args, **new_kwargs)

    def call(self, func, mapping=None, args=None, kwargs=None):
        new_args, new_kwargs = self._inject_services(func,
                                                     skip_self=False,
                                                     mapping=mapping or dict(),
                                                     args=args or tuple(),
                                                     kwargs=kwargs or dict())

        return func(*new_args, **new_kwargs)

    if PY3:
        def _inject_services(self, f, skip_self, mapping, args, kwargs):
            len_args = len(args) + (1 if skip_self else 0)
            signature = inspect.signature(f)

            kwargs = kwargs.copy()
            for name, parameter in islice(signature.parameters.items(),
                                          len_args, None):
                try:
                    service_name = mapping[name]
                except KeyError:
                    service_name = parameter.annotation

                if name not in kwargs and service_name is not parameter.empty:
                    try:
                        kwargs[name] = self._container[service_name]
                    except UndefinedServiceError:
                        pass

            bound_arguments = signature.bind_partial(*args, **kwargs)

            return bound_arguments.args, bound_arguments.kwargs
    else:
        def _inject_services(self, f, skip_self, mapping, args, kwargs):
            len_args = len(args) + (1 if skip_self else 0)
            try:
                arguments = inspect.getargspec(f).args
            except TypeError:
                pass
            else:
                kwargs = kwargs.copy()
                for name in islice(arguments, len_args, None):
                    if name not in kwargs:
                        try:
                            kwargs[name] = self._container[mapping[name]]
                        except (KeyError, UndefinedServiceError):
                            pass

            return args, kwargs


class ServiceContainer:
    def __init__(self):
        self._services_by_id = dict()
        self._services_by_type = dict()

        self.services = ChainMap(
            self._services_by_id,
            self._services_by_type,
        )
        self._services_instances = {}

    def __getitem__(self, item):
        try:
            return self._services_instances[item]
        except KeyError:
            try:
                service = self.services[item]
            except KeyError:
                raise UndefinedServiceError(item)
            else:
                try:
                    instance = service.instantiate()
                except Exception as e:
                    raise ServiceInstantiationError(repr(e))
                else:
                    if service.singleton:
                        self._services_instances[item] = instance
                    return instance

    def __setitem__(self, key, value):
        self._services_instances[key] = value

    def register(self, factory, singleton=False, type=None, id=None,
                 force=False):
        if type is None:
            type = factory
        service = Service(instantiate=factory, singleton=singleton)

        if type in self._services_by_type and not force:
            raise DuplicateServiceError(type)

        self._services_by_type[type] = service

        if id:
            if id in self._services_by_id and not force:
                raise DuplicateServiceError(id)

            self._services_by_id[id] = service

    def extend(self, container, override=False):
        if override:
            self.services = self.services.new_child(container.services)
        else:
            self.services.maps.append(container.services)


class Service:
    __slots__ = ('instantiate', 'singleton')

    def __init__(self, instantiate, singleton):
        self.instantiate = instantiate
        self.singleton = singleton
