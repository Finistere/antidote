from typing import Iterable, Union

from .register import register
from .wire import wire
from ..core import DEPENDENCIES_TYPE, DependencyContainer
from ..providers.lazy import LazyMethodCall


class LazyConfigurationMeta(type):
    def __new__(metacls, cls, bases, namespace,
                lazy_method: str = '__call__',
                auto_wire: Union[bool, Iterable[str]] = None,
                dependencies: DEPENDENCIES_TYPE = None,
                use_names: Union[bool, Iterable[str]] = None,
                use_type_hints: Union[bool, Iterable[str]] = None,
                container: DependencyContainer = None):
        if lazy_method not in namespace:
            raise ValueError(
                "Lazy method {} is no defined in {}".format(lazy_method, cls)
            )

        resource_class = super().__new__(metacls, cls, bases, namespace)

        wire_raise_on_missing = True
        if auto_wire is None or isinstance(auto_wire, bool):
            if auto_wire is False:
                methods = ()  # type: Iterable[str]
            else:
                methods = (lazy_method, '__init__')
                wire_raise_on_missing = False
        else:
            methods = auto_wire

        if methods:
            resource_class = wire(
                resource_class,
                methods=methods,
                dependencies=dependencies,
                use_names=use_names,
                use_type_hints=use_type_hints,
                container=container,
                raise_on_missing=wire_raise_on_missing
            )

        resource_class = register(
            resource_class,
            auto_wire=False,
            container=container,
            singleton=True
        )

        func = resource_class.__dict__[lazy_method]
        for k, v in resource_class.__dict__.items():
            if not k.startswith('_') and k.isupper():
                setattr(resource_class, k, LazyMethodCall(func, singleton=True)(v))

        return resource_class

    def __init__(metacls, cls, bases, namespace, **kwargs):  # pypy35 compatibility
        super().__init__(cls, bases, namespace)
