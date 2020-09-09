import inspect
from typing import Callable, TypeVar

from .inject import inject
from .._internal.utils import API
from ..providers import IndirectProvider

F = TypeVar('F', bound=Callable[[], type])
C = TypeVar('C', bound=type)


@API.public
def implements(interface: type, *, override: bool) -> Callable[[C], C]:
    """
    Class decorator declaring the underlying class as a (possible) implementation
    to be used by Antidote when requested the specified interface.

    For now, the underlying class needs to be decorated with @register.

    Args:
        interface: Interface implemented by the decorated class.

    Returns:
        The decorated class, unmodified.
    """
    if not inspect.isclass(interface):
        raise TypeError(f"interface must be a class, not a {type(interface)}")

    @inject
    def register_link(obj, indirect_provider: IndirectProvider):
        if inspect.isclass(obj):
            if not issubclass(obj, interface):
                raise TypeError(f"{obj} does not implement {interface}.")

            indirect_provider.register_static(interface, obj)
        else:
            raise TypeError(f"implements must be applied on a class, not a {type(obj)}")
        return obj

    return register_link


@API.experimental
def implementation(interface: type, *, static=True) -> Callable[[F], F]:
    """
    Function decorator which is expected to return a class implementing the specified
    interface. The class will be treated as a dependency itself and hence should be
    known to Antidote through @register typically.

    Args:
        interface: Interface for which an implementation will be provided
        static: Whether the returned implementation remains the same until the end.

    Returns:
        The decorated function, unmodified.
    """
    if not inspect.isclass(interface):
        raise TypeError(f"interface must be a class, not a {type(interface)}")

    @inject
    def register(func, indirect_provider: IndirectProvider):
        if inspect.isfunction(func):
            def linker():
                impl = func()
                if not isinstance(impl, type):
                    raise TypeError(f"{func!r} is expected to return a subclass "
                                    f"of {interface!r}")
                if not issubclass(impl, interface):
                    raise ValueError(f"{func!r} is expected to return a subclass "
                                     f"of {interface!r}")
                return impl
            indirect_provider.register_link(interface, linker=linker, static=static)
        else:
            raise TypeError(f"implements must be applied on a function, "
                            f"not a {type(func)}")
        return func

    return register
