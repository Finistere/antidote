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

    def register(self, service=None, id=None, singleton=True, auto_wire=None,
                 mapping=None, inject_by_name=None):
        auto_wire = self.auto_wire if auto_wire is None else auto_wire

        def _register(obj):
            if inspect.isclass(obj):
                if auto_wire:
                    if auto_wire is True:
                        to_wire = ('__init__',)
                    else:
                        to_wire = auto_wire
                    obj = self.wire(obj,
                                    functions=to_wire,
                                    mapping=mapping,
                                    inject_by_name=inject_by_name)
                self.container.register(factory=obj, singleton=singleton)
            else:
                self.container[id or type(obj)] = obj

            return obj

        return service and _register(service) or _register

    if PY3:
        def provider(self, service=None, returns=None, auto_wire=None,
                     singleton=True, mapping=None, inject_by_name=None):
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
                                        mapping=mapping,
                                        inject_by_name=inject_by_name)

                    service_id = obj.__call__.__annotations__.get('return')
                    obj = obj()
                else:
                    if auto_wire:
                        obj = self.inject(obj,
                                          mapping=mapping,
                                          inject_by_name=inject_by_name)
                    service_id = obj.__annotations__.get('return')

                service_id = returns or service_id

                if not service_id:
                    raise ValueError("Either a return annotation or the "
                                     "'returns' parameter must be not None.")

                self.container.register(factory=obj, singleton=singleton,
                                        type=service_id)
                return obj

            return service and _provider(service) or _provider
    else:
        def provider(self, service=None, returns=None, auto_wire=None,
                     singleton=True, mapping=None, inject_by_name=None):
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
                                        mapping=mapping,
                                        inject_by_name=inject_by_name)
                    obj = obj()
                elif auto_wire:
                    obj = self.inject(obj,
                                      mapping=mapping,
                                      inject_by_name=inject_by_name)

                self.container.register(factory=obj, type=returns,
                                        singleton=singleton)
                return obj

            return service and _provider(service) or _provider

    def wire(self, cls=None, functions=None, **inject_kwargs):
        def _wire(cls):
            for f in functions:
                setattr(cls, f, self.inject(getattr(cls, f), **inject_kwargs))

            return cls

        return cls and _wire(cls) or _wire

    def inject(self, func=None, mapping=None, inject_by_name=None):
        if inject_by_name is None:
            inject_by_name = self.inject_by_name
        mapping = mapping or dict()
        arg_mapping = []  # cannot use nonlocal because of Python 2.7 ...
        gen_args_kwargs = self.builder.generate_injected_args_kwargs

        @wrapt.decorator
        def _inject(wrapped, instance, args, kwargs):
            if not arg_mapping:
                arg_mapping.append(self.builder.generate_arguments_mapping(
                    wrapped, inject_by_name=inject_by_name,
                    mapping=mapping,
                ))

            args, kwargs = gen_args_kwargs(arg_mapping[0], args, kwargs)
            return wrapped(*args, **kwargs)

        return func and _inject(func) or _inject

    def attrib(self, service=None, inject_by_name=None, **kwargs):
        if inject_by_name is None:
            inject_by_name = self.inject_by_name

        try:
            import attr
        except ImportError:
            raise RuntimeError('attrs package must be installed.')

        def attrib_factory(instance):
            try:
                service_name = attrib_factory.service_name
            except AttributeError:
                if service is None:
                    cls = instance.__class__
                    for name, value in cls.__dict__.items():
                        # Dirty way to find the attrib annotation.
                        # Maybe attr will eventually provide the annotation ?
                        if isinstance(value, attr.Attribute) \
                                and isinstance(value.default, attr.Factory) \
                                and value.default.factory is attrib_factory:
                            try:
                                service_name = cls.__annotations__[name]
                            except (AttributeError, KeyError):
                                if inject_by_name:
                                    service_name = name
                                    break
                            else:
                                break
                    else:
                        raise ValueError(
                            "Either an annotation or the 'service' "
                            "parameter must be not None."
                        )
                else:
                    service_name = service

                attrib_factory.service_name = service_name

            return self.container[service_name]

        return attr.ib(default=attr.Factory(attrib_factory, takes_self=True),
                       **kwargs)
