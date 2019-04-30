from enum import Flag
from typing import Callable, cast, TypeVar

from .._internal.default_container import get_default_container
from ..core import DependencyContainer
from ..providers import InterfaceProvider

T = TypeVar('T')


def implements(interface: type,
               *,
               profile: Flag = None,
               container: DependencyContainer = None) -> Callable[[T], T]:
    container = container or get_default_container()

    def register_implementation(cls):
        interface_provider = cast(InterfaceProvider,
                                  container.providers[InterfaceProvider])
        interface_provider.register(interface, cls, profile)

        return cls

    return register_implementation
