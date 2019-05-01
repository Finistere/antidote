import inspect
from enum import Flag
from typing import Callable, cast, TypeVar

from .._internal.default_container import get_default_container
from ..core import DependencyContainer
from ..providers import IndirectProvider

T = TypeVar('T', bound=type)


def implements(interface: type,
               *,
               context: Flag = None,
               container: DependencyContainer = None) -> Callable[[T], T]:
    """
    Class decorator declaring the underlying class as a (possible) implementation
    to be used by Antidote when requested the specified interface.

    Args:
        interface: Interface implemented by the decorated class.
        context: If multiple implementations exist for an interface, a custom
            :py:class:`~enum.Flag` should be used to identify all the different
            possible contexts. Each implementation should be associated with one
            context or a combination of them. At runtime Antidote will retrieve
            the current context through the custom :py:class:`~enum.Flag` class.
        container: :py:class:`~.core.container.DependencyContainer` from which
            the dependencies should be retrieved. Defaults to the global
            core if it is defined.

    Returns:
        The decorated class, unmodified.
    """
    container = container or get_default_container()

    def register_implementation(cls):
        if not inspect.isclass(cls):
            raise TypeError(f"implements must be applied on a class, "
                            f"not a {type(cls)}")

        if not issubclass(cls, interface):
            raise TypeError(f"{cls} does not implement {interface}.")

        interface_provider = cast(IndirectProvider,
                                  container.providers[IndirectProvider])
        interface_provider.register(interface, cls, context)

        return cls

    return register_implementation
