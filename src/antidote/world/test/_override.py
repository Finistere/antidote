from typing import (Any, Callable, Dict, Hashable, Optional, TypeVar, Union, overload)

from ..._compatibility.typing import get_type_hints
from ..._internal import API, state
from ...core.container import (DependencyValue, Scope)
from ...utils import validated_scope

__sentinel = object()


@overload
def singleton(dependency: Hashable,  # noqa: E704  # pragma: no cover
              value: object
              ) -> None: ...


@overload
def singleton(dependency: Dict[Hashable, object]  # noqa: E704  # pragma: no cover
              ) -> None: ...


@API.public
def singleton(dependency: Union[Dict[Hashable, object], Hashable],
              value: object = __sentinel) -> None:
    """
    Override one or multiple dependencies with one/multiple singletons.

    .. doctest:: world_test_override_singleton

        >>> from antidote import world, Service
        >>> class MyService(Service):
        ...     pass
        >>> world.get(MyService)
        <MyService ...>
        >>> with world.test.clone():
        ...     # dependencies can also be overridden as many times as necessary
        ...     world.test.override.singleton(MyService, "fake service")
        ...     # Within the cloned world, we changed the dependency value of MyService
        ...     world.get(MyService)
        'fake service'

    Args:
        dependency: Singleton to declare, must be hashable. If a dict is provided, it'll
            be treated as a dictionary of singletons to add.
        value: Associated value for the dependency.

    """
    if value is __sentinel:
        if isinstance(dependency, dict):
            state.current_overridable_container().override_singletons(dependency)
        else:
            raise TypeError("If only a single argument is provided, "
                            "it must be a dictionary of singletons.")
    else:
        if isinstance(dependency, dict):
            raise TypeError("A dictionary cannot be used as a key.")
        state.current_overridable_container().override_singletons({dependency: value})


F = TypeVar('F', bound=Callable[..., Any])


@API.public
def factory(dependency: Hashable = None,
            *,
            singleton: bool = None,
            scope: Optional[Scope] = Scope.sentinel()
            ) -> Callable[[F], F]:
    """
    Override a dependency with the result of a factory. To be used as a function
    decorator. The result of the underlying function, the factory, will be used as the
    associated value of the dependency.

    .. doctest:: world_test_override_factory

        >>> from antidote import world, Service
        >>> class MyService(Service):
        ...     pass
        >>> world.get(MyService)
        <MyService ...>
        >>> with world.test.clone():
        ...     @world.test.override.factory(MyService)
        ...     def test():
        ...         return "fake service"
        ...     # Within the cloned world, we changed the dependency value of MyService
        ...     world.get(MyService)
        'fake service'
        >>> with world.test.clone():
        ...     # If not specified explicitly, the return type hint will be used
        ...     # as the dependency.
        ...     @world.test.override.factory()
        ...     def test() -> MyService:
        ...         return "fake service"
        ...     world.get(MyService)
        'fake service'

    Args:
        dependency: Dependency to override.
        singleton: Whether the returned dependency  is a singleton or not. If yes,
            the factory will be called at most once and the result re-used. Mutually
            exclusive with :code:`scope`. Defaults to :py:obj:`True`.
        scope: Scope of the returned dependency. Mutually exclusive with
            :code:`singleton`. The scope defines if and how long the returned dependency
            will be cached. See :py:class:`~.core.container.Scope`. Defaults to
            :py:meth:`~.core.container.Scope.singleton`.

    .. note::

        As all override work as a single layer on top of the usual dependencies, if the
        dependency is already overridden as a singleton, the factory won't be called.
        Overrides done with a provider also have a higher priority. See
        :py:mod:`.world.test.override`.

    Returns:
        The decorated function, unchanged.
    """
    scope = validated_scope(scope, singleton, default=Scope.singleton())

    def decorate(f: F) -> F:
        if not callable(f):
            raise TypeError(f"factory must be a callable, not a {type(f)}")
        if dependency is None:
            output = get_type_hints(f).get('return')
            if output is None:
                raise ValueError("Either the dependency argument or the return type hint "
                                 "of the factory must be specified")
        else:
            output = dependency
        state.current_overridable_container() \
            .override_factory(output, factory=f, scope=scope)
        return f

    return decorate


P = TypeVar('P', bound=Callable[[Any], Optional[DependencyValue]])


@API.public
def provider() -> Callable[[P], P]:
    """
    Function decorator used to declare a simplified provider to override some
    dependencies. The function will be called for each dependency and should
    return :py:class:`.core.DependencyValue` if it can be provided or :py:obj:`None`
    if not.

    .. doctest:: world_test_override_provider

        >>> from antidote import world, Service
        >>> from antidote.core import DependencyValue, Scope
        >>> class MyService(Service):
        ...     pass
        >>> world.get(MyService)
        <MyService ...>
        >>> with world.test.clone():
        ...     @world.test.override.provider()
        ...     def test(dependency):
        ...         if dependency is MyService:
        ...             return DependencyValue('fake service', scope=Scope.singleton())
        ...     # Within the cloned world, we changed the dependency value of MyService
        ...     world.get(MyService)
        'fake service'

    .. note::

        As all override work as a single layer on top of the usual dependencies, singleton
        overrides won't pass through the provider. See :py:mod:`.world.test.override`.

    .. warning::

        Beware of :py:func:`~.world.test.override.provider`, it can conflict with
        :py:func:`~.world.test.override.factory` and
        :py:func:`~.world.test.override.singleton`.
        Dependencies declared with :py:func:`~.world.test.override.singleton` will hide
        :py:func:`~.world.test.override.provider`. And
        :py:func:`~.world.test.override.provider` will hide
        :py:func:`~.world.test.override.factory`.

        Moreover it won't appear in :py:func:`.world.debug`.

    Returns:
        Function decorator.
    """

    def decorate(p: P) -> P:
        if not callable(p):
            raise TypeError(f"provider must be a callable, not {type(p)}")
        state.current_overridable_container().override_provider(p)
        return p

    return decorate
