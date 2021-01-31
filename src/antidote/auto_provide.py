from typing import (Any, Callable, TypeVar, Union, overload)

from ._internal import API
from .core.injection import inject

F = TypeVar('F')
AnyF = Union[Callable[..., Any], staticmethod, classmethod]


@overload
def auto_inject(*positional_dependencies  # pragma: no cover
                ) -> Callable[[F], F]: ...


@overload
def auto_inject(**named_dependencies  # pragma: no cover
                ) -> Callable[[F], F]: ...


@API.public
def auto_inject(*positional_dependencies, **named_dependencies) -> Callable[[F], F]:
    """
    Syntactic sugar for :py:func:`.inject`.

    :py:func:`.inject` is designed to be very flexible and strict, everything is explicit.
    Thus it can become a bit verbose in most cases, hence the :py:func:`.auto_inject`
    which tries to be as simple as possible for the general use case.

    The core difference with :py:func:`.inject` is that :code:`auto_provide` is
    :code:`True` by default. Meaning that Antidote will automatically try to inject any
    argument that had a class as a type hint:

    .. doctest:: auto_inject

        >>> from antidote import world, Service, auto_inject
        >>> class MyService(Service):
        ...     pass
        >>> @auto_inject
        ... def f(s: MyService):
        ...     return s
        >>> f() is world.get(MyService)
        True
        >>> # is equivalent to:
        ... @inject(auto_provide=True)
        ... def f(s: MyService):
        ...     return s

    Of course, those will only be injected if they really are declared as dependencies:

    .. doctest:: auto_inject

        >>> class Unknown:
        ...     pass
        >>> @auto_inject
        ... def f(s: Unknown):
        ...     return s
        >>> f()
        Traceback (most recent call last):
        ...
        DependencyNotFoundError: Unknown
        >>> # @inject will also fail, but it never tried to inject
        ... # anything at all here
        ... @inject
        ... def f(s: Unknown):
        ...     return s
        >>> f()
        Traceback (most recent call last):
        ...
        TypeError: f() missing 1 required positional argument: 's'

    :py:func:`.auto_inject` also provides a simpler API to define for each argument which
    dependencies should be used. You can either specify them by name:

    .. doctest:: auto_inject

        >>> class Second(Service):
        ...     pass
        >>> @auto_inject(a=MyService, b=Second)
        ... def f(a, b):
        ...     return a, b
        >>> f() == (world.get(MyService), world.get(Second))
        True
        >>> # is equivalent to:
        ... @inject(dependencies=dict(a=MyService, b=Second))
        ... def f(a, b):
        ...     return a, b

    Or by position:

    .. doctest:: auto_inject

        >>> @auto_inject(MyService, Second)
        ... def f(a, b):
        ...     return a, b
        >>> f() == (world.get(MyService), world.get(Second))
        True
        >>> # is equivalent to:
        ... @inject(dependencies=(MyService, Second))
        ... def f(a, b):
        ...     return a, b
        >>> sentinel = object()
        >>> # You can skip arguments with None
        ... @auto_inject(None, Second)
        ... def f(a=sentinel, b=sentinel):
        ...     return a, b
        >>> f() == (sentinel, world.get(Second))
        True

    Returns:
        Function decorator or the injected function if the :code:`__func` was supplied.
    """
    if positional_dependencies and named_dependencies:
        raise ValueError("Either use only positional or named dependencies, not both.")

    dependencies = positional_dependencies or named_dependencies

    def decorate(__func: F) -> F:
        return inject(__func,
                      auto_provide=True,
                      dependencies=dependencies)

    return decorate
