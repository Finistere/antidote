import inspect

import wrapt

from ._compat import PY3
from .builder import Builder
from .container import Container


class ServiceManager:
    """
    Provides utility functions/decorators to manage the container.
    """
    auto_wire = True
    inject_by_name = False

    def __init__(self, auto_wire=None, inject_by_name=None,
                 container_class=Container, builder_class=Builder):
        if auto_wire is not None:
            self.auto_wire = auto_wire
        if inject_by_name is not None:
            self.inject_by_name = inject_by_name

        self.container = container_class()
        self.builder = builder_class(self.container)

    @classmethod
    def name_to_parameter(cls, name):
        return name.split('_', 1)

    def register(self, service=None, id=None, singleton=True, auto_wire=None,
                 **inject_kwargs):
        auto_wire = self.auto_wire if auto_wire is None else auto_wire

        if service and not inspect.isclass(service) and not id:
            raise ValueError("Parameter 'id' cannot be None when registering"
                             "an instance as a service.")

        def _register(obj):
            if inspect.isclass(obj):
                if auto_wire:
                    if auto_wire is True:
                        to_wire = ('__init__',)
                    else:
                        to_wire = auto_wire
                    obj = self.wire(obj,
                                    functions=to_wire,
                                    **inject_kwargs)
                self.container.register(factory=obj, singleton=singleton)
            else:
                self.container[id] = obj

            return obj

        return service and _register(service) or _register

    if PY3:
        def provider(self, service=None, returns=None, auto_wire=None,
                     **inject_kwargs):
            auto_wire = self.auto_wire if auto_wire is None else auto_wire

            def _provider(obj):
                if inspect.isclass(obj):
                    if auto_wire:
                        if auto_wire is True:
                            to_wire = ('__call__', '__init__')
                        else:
                            to_wire = auto_wire
                        obj = self.wire(obj,
                                        functions=to_wire,
                                        **inject_kwargs)

                    service_id = obj.__call__.__annotations__['return']
                    obj = obj()
                else:
                    if auto_wire:
                        obj = self.inject(obj, **inject_kwargs)

                    service_id = obj.__annotations__['return']

                service_id = returns or service_id

                if not service_id:
                    raise ValueError("Either a return annotation or the "
                                     "'returns' parameter must be not None.")

                self.container.register(factory=obj, singleton=False,
                                        type=returns or service_id)
                return obj

            return service and _provider(service) or _provider
    else:
        def provider(self, service=None, returns=None, auto_wire=None,
                     **inject_kwargs):
            auto_wire = self.auto_wire if auto_wire is None else auto_wire

            if returns is None:
                raise ValueError("Either a return annotation or the "
                                 "'returns' parameter must be not None.")

            def _provider(obj):
                if inspect.isclass(obj):
                    if auto_wire:
                        if auto_wire is True:
                            to_wire = ('__call__', '__init__')
                        else:
                            to_wire = auto_wire
                        obj = self.wire(obj,
                                        functions=to_wire,
                                        **inject_kwargs)
                    obj = obj()
                elif auto_wire:
                    obj = self.inject(obj, **inject_kwargs)

                self.container.register(factory=obj, type=returns,
                                        singleton=False)
                return obj

            return service and _provider(service) or _provider

    def wire(self, cls=None, functions=None, **inject_kwargs):
        def _wire(cls):
            for f in functions:
                setattr(cls, f,
                        self.inject(getattr(cls, f), **inject_kwargs))

            return cls

        return cls and _wire(cls) or _wire

    def inject(self, func=None, mapping=None, inject_by_name=None):
        if inject_by_name is None:
            inject_by_name = self.inject_by_name

        @wrapt.decorator
        def _inject(wrapped, instance, args, kwargs):
            return self.builder.call(wrapped, mapping=mapping,
                                     kwargs=kwargs, args=args,
                                     inject_by_name=inject_by_name)

        return func and _inject(func) or _inject

    def attrib(self, service=None, **kwargs):
        try:
            import attr
        except ImportError:
            raise RuntimeError('attrs package must be installed.')

        def attrib_factory(instance):
            if service is None:
                cls = instance.__class__
                for name, value in cls.__dict__.items():
                    # Dirty way to find the attrib annotation.
                    # Maybe attr will eventually provide the annotation ?
                    if isinstance(value, attr.Attribute) \
                            and isinstance(value.default, attr.Factory) \
                            and value.default.factory is attrib_factory:
                        return self.container[cls.__annotations__[name]]

                raise ValueError("Either an annotation or the 'service' "
                                 "parameter must be not None.")

            return self.container[service]

        return attr.ib(default=attr.Factory(attrib_factory, takes_self=True),
                       **kwargs)
