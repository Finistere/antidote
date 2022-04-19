from __future__ import annotations

import inspect
from typing import Callable, cast, Optional, overload, TypeVar, Union

from typing_extensions import ParamSpec, Protocol

from ._lazy import LazyWrapper, LazyWrapperWithoutScope
from ..._internal import API
from ...core import inject, Scope
from ...core.annotations import HiddenDependency
from ...core.exceptions import DoubleInjectionError
from ...utils import validated_scope

__all__ = ['LazyWrappedFunction', 'lazy']

P = ParamSpec('P')
T = TypeVar('T')
Out = TypeVar('Out', covariant=True)


@API.public
class LazyWrappedFunction(Protocol[P, Out]):
    """
    .. versionadded:: 1.4

    Wrapper protocol of a wrapped :py:func:`.lazy` function. The underlying function can be
    accessed directly through :py:attr:`~.LazyWrappedFunction.__wrapped__` and can be called
    directly with :py:meth:`~.LazyWrappedFunction.call` for convenience.
    """

    @property
    def __wrapped__(self) -> Callable[P, Out]:
        """
        Actual function wrapped by :py:func:`.lazy`.
        """
        ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> HiddenDependency[Out]:
        """
        Creates a dependency which will execute the wrapped function with the given arguments
        only when needed.

        .. doctest:: lib_lazy_lazy_wrapped_function__call__

            >>> from antidote import lazy, inject
            >>> @lazy
            ... def hello(name: str) -> str:
            ...     print("Executing...")
            ...     return f"Hello {name}!"
            >>> @inject
            ... def f(msg: str = hello("John")) -> str:
            ...     return msg
            >>> f()
            Executing...
            'Hello John!'
        """
        ...

    def call(self, *args: P.args, **kwargs: P.kwargs) -> Out:
        """
        Provides a convenient method to call the underlying function directly:

        .. doctest:: lib_lazy_lazy_wrapped_function_call

            >>> from antidote import lazy, inject
            >>> @lazy
            ... def hello(name: str) -> str:
            ...     print("Executing...")
            ...     return f"Hello {name}!"
            >>> hello.call("John")
            Executing...
            'Hello John!'

        """
        ...


@overload
def lazy(*,
         singleton: Optional[bool] = None,
         scope: Optional[Scope] = Scope.sentinel()
         ) -> Callable[[Callable[P, T]], LazyWrappedFunction[P, T]]:
    ...


@overload
def lazy(__func: Callable[P, T],
         *,
         singleton: Optional[bool] = None,
         scope: Optional[Scope] = Scope.sentinel()
         ) -> LazyWrappedFunction[P, T]:
    ...


@API.public
def lazy(__func: Optional[Callable[P, T]] = None,
         *,
         singleton: Optional[bool] = None,
         scope: Optional[Scope] = Scope.sentinel()
         ) -> Union[LazyWrappedFunction[P, T],
                    Callable[[Callable[P, T]], LazyWrappedFunction[P, T]]]:
    """
    .. versionadded:: 1.4

    Decorated function will now return a dependency allowing lazy execution with :py:obj:`.inject`.

    .. doctest:: lib_lazy_lazy

        >>> import os
        >>> from antidote import inject, lazy, world
        >>> class Template:
        ...     pass
        >>> @lazy
        ... def main_template() -> Template:
        ...     print("*Called main_template.*")
        ...     return Template()
        >>> @inject
        ... def f(t: Template = main_template()) -> Template:
        ...     return t
        >>> f()
        *Called main_template.*
        <Template ...>
        >>> world.get(main_template())
        <Template ...>

    The original function is still accessible through :py:attr:`~.LazyWrappedFunction.__wrapped__`
    and for convenience :py:meth:`~.LazyWrappedFunction.call` can be used to call it.

    .. doctest:: lib_lazy_lazy

        >>> main_template.call()
        *Called main_template.*
        <Template ...>
        >>> main_template.__wrapped__
        <function main_template ...>

    By default the function returns a singleton:

    .. doctest:: lib_lazy_lazy

        >>> @lazy
        ... def root() -> Template:
        ...     return Template()
        >>> world.get[Template](root()) is world.get[Template](root())
        True
        >>> @lazy(singleton=False)
        ... def tmp() -> Template:
        ...     return Template()
        >>> world.get[Template](tmp()) is world.get[Template](tmp())
        False

    Arguments are also taken into account. The same instance is returned if arguments are equal.
    The arguments MUST be hashable.

    .. doctest:: lib_lazy_lazy

        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class Template:
        ...     name: str
        >>> @lazy
        ... def template(name: str) -> Template:
        ...     return Template(name=name)
        >>> @inject
        ... def f(x: Template = template(name='test')) -> Template:
        ...     return x
        >>> f() is f()
        True

    Args:
        __func: **/positional-only/** Function to wrap, which will be called lazily for
            dependencies.
        singleton: Whether the injectable is a singleton or not. A singleton is instantiated only
            once. Mutually exclusive with :code:`scope`. Defaults to :py:obj:`True`
        scope: Scope of the service. Mutually exclusive with :code:`singleton`.  The scope defines
            if and how long the service will be cached. See :py:class:`~.core.container.Scope`.
            Defaults to :py:meth:`~.core.container.Scope.singleton`.

    Returns:
        A :py:class:`.LazyWrappedFunction` or a function decorator to create it.
    """
    scope = validated_scope(scope, singleton, default=Scope.singleton())

    def decorate(func: Callable[P, T]) -> LazyWrappedFunction[P, T]:
        if not (callable(func) and inspect.isfunction(func)):
            raise TypeError("lazy can only be applied on a function.")

        # for PyRight because we use the inspect.isfunction type guard.
        func = cast(Callable[P, T], func)

        try:
            func = inject(func)
        except DoubleInjectionError:
            pass

        if scope is None:
            return LazyWrapperWithoutScope[P, T](func=func)
        return LazyWrapper[P, T](func=func, scope=scope)

    return __func and decorate(__func) or decorate
