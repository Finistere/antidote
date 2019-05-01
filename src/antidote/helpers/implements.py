import inspect
from enum import Flag
from typing import Callable, cast, TypeVar

from .._internal.default_container import get_default_container
from ..core import DependencyContainer
from ..providers import IndirectProvider

T = TypeVar('T')


def implements(interface: type,
               *,
               profile: Flag = None,
               container: DependencyContainer = None) -> Callable[[T], T]:
    container = container or get_default_container()

    def register_implementation(cls):
        if not inspect.isclass(cls):
            raise TypeError(f"implements must be applied on a class, "
                            f"not a {type(cls)}")

        if not issubclass(cls, interface):
            raise TypeError(f"{cls} does not implement {interface}.")

        interface_provider = cast(IndirectProvider,
                                  container.providers[IndirectProvider])
        interface_provider.register(interface, cls, profile)

        return cls

    return register_implementation
