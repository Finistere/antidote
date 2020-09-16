import inspect
from typing import Callable, TypeVar

from .._internal import API
from ..core import inject
from ..providers import IndirectProvider
from ..providers.factory import FactoryDependency
from ..providers.service import Build

F = TypeVar('F', bound=Callable[[], type])
C = TypeVar('C', bound=type)


@API.public
def implements(interface: type) -> Callable[[C], C]:
    """
    Class decorator declaring the underlying class as the implementation
    to be used by Antidote when requested the specified interface.

    The underlying class needs to be retrievable from Antidote, typically by
    defining it as a service:

    .. doctest::

        >>> from antidote import world, implements, Service
        >>> class Interface:
        ...     pass
        >>> @implements(Interface)
        ... class Impl(Interface, Service):
        ...     pass
        >>> world.get(Interface)
        Impl

    .. note::

        If you need to chose between multiple implementations use
        :py:func:`.implementation`.

    Args:
        interface: Interface implemented by the decorated class.

    Returns:
        The decorated class, unmodified.
    """
    if not inspect.isclass(interface):
        raise TypeError(f"interface must be a class, not a {type(interface)}")

    @inject
    def register_implementation(obj, indirect_provider: IndirectProvider):
        if inspect.isclass(obj):
            if not issubclass(obj, interface):
                raise TypeError(f"{obj} does not implement {interface}.")

            indirect_provider.register_static(interface, obj)
        else:
            raise TypeError(f"implements must be applied on a class, not a {type(obj)}")
        return obj

    return register_implementation


@API.experimental
def implementation(interface: type, *, permanent=True) -> Callable[[F], F]:
    """
    Function decorator which decides which implementation should be used for
    :code:`interface`.

    The underlying function is expected to return a dependency, typically the class of
    the implementation when defined as a service. You may also use a factory dependency.

    The function will not be wired, you'll need to do it yourself if you need it.

    .. doctest::

        >>> from antidote import implementation, Service, factory, world
        >>> class Interface:
        ...     pass
        >>> class A(Interface, Service):
        ...     pass
        >>> class B(Interface):
        ...     pass
        >>> @factory
        ... def build_b() -> B:
        ...     return B()
        >>> @implementation(Interface)
        ... @inject(dependencies=['choice'])
        ... def choose_interface(choice: str):
        ...     if choice == 'a':
        ...         return A  # One could also use A.with_kwargs(...)
        ...     else:
        ...         return B @ build_b  # or B @ build_b.with_kwargs(...)
        >>> world.singletons.set('choice', 'b')
        ... world.get(Interface)
        B
        >>> # Changing choice doesn't matter anymore as the implementation is permanent.
        ... world.singletons.set('choice', 'a')
        ... world.get(Interface)
        B

    Args:
        interface: Interface for which an implementation will be provided
        permanent: Whether the function should be called each time the interface is needed
            or not. Defaults to :py:obj:`True`.

    Returns:
        The decorated function, unmodified.
    """
    if not inspect.isclass(interface):
        raise TypeError(f"interface must be a class, not a {type(interface)}")

    @inject
    def register(func, indirect_provider: IndirectProvider):
        if inspect.isfunction(func):
            def linker():
                dependency = func()
                cls = dependency
                if isinstance(cls, Build):
                    cls = cls.dependency
                if isinstance(cls, FactoryDependency):
                    cls = cls.dependency

                if not (isinstance(cls, type) and inspect.isclass(cls)
                        and issubclass(cls, interface)):
                    raise TypeError(f"{func} is expected to return a class or a "
                                    f"Service / Factory dependency which implements"
                                    f"{interface}")
                return dependency

            indirect_provider.register_link(interface, linker=linker, permanent=permanent)
        else:
            raise TypeError(f"implementation must be applied on a function, "
                            f"not a {type(func)}")
        return func

    return register
