import inspect
from enum import Enum
from typing import Callable, cast, TypeVar

from .._internal.default_container import get_default_container
from ..core import DependencyContainer
from ..providers import IndirectProvider

T = TypeVar('T', bound=type)


def implements(interface: type,
               *,
               state: Enum = None,
               container: DependencyContainer = None) -> Callable[[T], T]:
    """
    Class decorator declaring the underlying class as a (possible) implementation
    to be used by Antidote when requested the specified interface.

    For now, the underlying class needs to be decorated with @register.

    Args:
        interface: Interface implemented by the decorated class.
        state: If multiple implementations exist for an interface, an
            :py:class:`~enum.Enum` should be used to identify all the possible
            states the application may be. Each state should be associated with
            one implementation. At runtime Antidote will retrieve the state
            (the :py:class:`~enum.Enum`) class to determine the current state.
        container: :py:class:`~.core.container.DependencyContainer` from which
            the dependencies should be retrieved. Defaults to the global
            container if it is defined.

    Returns:
        The decorated class, unmodified.
    """
    container = container or get_default_container()

    def register_implementation(cls):
        if not inspect.isclass(cls):
            raise TypeError("implements must be applied on a class, "
                            "not a {}".format(type(cls)))

        if not issubclass(cls, interface):
            raise TypeError("{} does not implement {}.".format(cls, interface))

        interface_provider = cast(IndirectProvider,
                                  container.providers[IndirectProvider])
        interface_provider.register(interface, cls, state)

        return cls

    return register_implementation
