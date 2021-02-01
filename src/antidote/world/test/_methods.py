from contextlib import contextmanager
from typing import (Any, Callable, Dict, Hashable, Iterator, Optional, TypeVar, Union,
                    get_type_hints, overload)

from ..._internal import API, state
from ..._providers.world_test import WorldTestProvider
from ...core import Provide, inject
from ...core.container import DependencyValue, RawContainer, RawProvider, Scope
from ...core.exceptions import DependencyNotFoundError
from ...utils import validated_scope


@API.public
@contextmanager
def clone(*,
          keep_singletons: bool = False,
          keep_scopes: bool = False
          ) -> Iterator[None]:
    """
    Clone the current container, namely scopes and providers. Existing singletons and
    scopes depdency values can also be propagated. Its primary use is to test existing
    dependencies. Hence the world will already be frozen but overridding dependencies
    will be possible.

    .. doctest:: world_test_clone

        >>> from antidote import world, Service
        >>> class MyService(Service):
        ...     pass
        >>> # Declared dependencies are available
        ... with world.test.clone():
        ...     world.get[MyService]()
        <MyService object ...>
        >>> s = world.get[MyService]()
        >>> # But by default singletons are NOT kept
        ... with world.test.clone():
        ...     world.get[MyService]() is s
        False
        >>> # which is of course configurable
        ... with world.test.clone(keep_singletons=True):
        ...     world.get[MyService]() is s
        True
        >>> # You'll keep the same objects though, so be careful !
        ... with world.test.clone(keep_singletons=True):
        ...     world.get[MyService]().new_attr = "hello"
        >>> world.get[MyService]().new_attr
        'hello'
        >>> # You cannot define new dependencies
        ... with world.test.clone():
        ...     class NewService(Service):
        ...         pass
        Traceback (most recent call last):
        ...
        FrozenWorldError
        >>> # but they can be overridden
        ... with world.test.clone():
        ...     # dependencies can also be overridden as many times as necessary
        ...     world.test.override.singleton(MyService, "fake service")
        ...     world.get(MyService)
        'fake service'

    Args:
        keep_singletons: Whether current singletons should be kept in the new world.
            Beware that the same objects will be propagated. Defaults to :py:obj:`False`.
        keep_scopes: Whether current dependency values within the existing scopes should
            be kept in the new world. Like :code:`keep_singletons`, the same objects will
            be propagated. Defaults to :py:obj:`False`.

    Returns:
        context manager within you can make your tests.

    """

    def build(c: RawContainer) -> RawContainer:
        return c.clone(keep_singletons=keep_singletons,
                       keep_scopes=keep_scopes)

    with state.override(build):
        yield


@API.public
@contextmanager
def new() -> Iterator[None]:
    """
    Creates a new container with the same kind of providers and scopes. So it doesn't
    have any dependencies defined, but any scope or provider added will be present.

    .. doctest:: world_test_new

        >>> from antidote import world
        >>> with world.test.new():
        ...     # Current world is empty but has the same providers and scope as the
        ...     # original one.
        ...     # You can define dependencies locally with world.test.singleton or factory
        ...     world.test.singleton("test", 1)
        ...     world.get[int]("test")
        ...
        1
        >>> # Anything done within the context manager stays there.
        ... world.get[int]("test")
        Traceback (most recent call last):
        ...
        DependencyNotFoundError: 'test'

    """

    def build_new_container(existing: RawContainer) -> RawContainer:
        c = RawContainer.with_same_providers_and_scopes(existing)
        try:
            c.get(WorldTestProvider)
        except DependencyNotFoundError:
            c.add_provider(WorldTestProvider)
        return c

    with state.override(build_new_container):
        yield


#######################################
# Utilities usable inside test worlds #
#######################################

__sentinel = object()


@overload
def singleton(dependency: Hashable,  # noqa: E704  # pragma: no cover
              value: object
              ) -> None: ...


@overload
def singleton(dependency: Dict[Hashable, object]  # noqa: E704  # pragma: no cover
              ) -> None: ...


@API.public
@inject
def singleton(dependency: Union[Dict[Hashable, object], Hashable],
              value: object = __sentinel,
              test_provider: Provide[WorldTestProvider] = None) -> None:
    """
    Declare one or multiple singleton dependencies with its associated value.

    .. doctest:: world_test_singleton

        >>> from antidote import world
        >>> with world.test.new():  # or empty()
        ...     world.test.singleton("test", 1)
        ...     world.get[int]("test")
        1

    Args:
        dependency: Singleton to declare, must be hashable. If a dict is provided, it'll
            be treated as a dictionary of singletons to add.
        value: Associated value for the dependency.

    """
    if test_provider is None:
        raise RuntimeError("Test singletons can only be added inside a test world "
                           "created with world.test.new() or world.test.empty()")
    if value is __sentinel:
        if isinstance(dependency, dict):
            test_provider.add_singletons(dependency)
        else:
            raise TypeError("If only a single argument is provided, "
                            "it must be a dictionary of singletons.")
    else:
        if isinstance(dependency, dict):
            raise TypeError("A dictionary cannot be used as a key.")
        test_provider.add_singletons({dependency: value})


F = TypeVar('F', bound=Callable[..., Any])


@API.public
def factory(dependency: Hashable = None,
            *,
            singleton: bool = None,
            scope: Optional[Scope] = Scope.sentinel()
            ) -> Callable[[F], F]:
    """
    Declare one or multiple singleton dependencies with its associated value.

    .. doctest:: world_test_factory

        >>> from antidote import world
        >>> class Dummy:
        ...     pass
        >>> with world.test.new():  # or empty()
        ...     @world.test.factory()
        ...     def build_dummy() -> Dummy:
        ...         return Dummy()
        ...     world.get[Dummy]()
        <Dummy ...>
        >>> with world.test.new():
        ...     # You don't need to rely on type hints
        ...     @world.test.factory(Dummy)
        ...     def build_dummy():
        ...         return Dummy()
        ...     world.get[Dummy]()
        <Dummy ...>

    Args:
        dependency: Dependency to override.
        singleton: Whether the returned dependency  is a singleton or not. If yes,
            the factory will be called at most once and the result re-used. Mutually
            exclusive with :code:`scope`. Defaults to :py:obj:`True`.
        scope: Scope of the returned dependency. Mutually exclusive with
            :code:`singleton`. The scope defines if and how long the returned dependency
            will be cached. See :py:class:`~.core.container.Scope`. Defaults to
            :py:meth:`~.core.container.Scope.singleton`.

    """
    scope = validated_scope(scope, singleton, default=Scope.singleton())

    @inject
    def decorate(f: F, test_provider: Provide[WorldTestProvider] = None) -> F:
        if test_provider is None:
            raise RuntimeError("Test singletons can only be added inside a test world "
                               "created with world.test.new()")
        if not callable(f):
            raise TypeError(f"factory must be a callable, not a {type(f)}")
        if dependency is None:
            output = get_type_hints(f).get('return')
            if output is None:
                raise ValueError("Either the dependency argument or the return type hint "
                                 "of the factory must be specified")
        else:
            output = dependency
        test_provider.add_factory(output, factory=f, scope=scope)
        return f

    return decorate


###############################
# Utilities to test providers #
###############################

@API.public
@contextmanager
def empty() -> Iterator[None]:
    """
    Only used to test providers.

    Creates an empty container. No initial providers are set up. This is useful to test
    one or several providers in isolation. If you're not testing provider, consider use
    :py:func:`.new` instead.
    """

    def build_container(_: RawContainer) -> RawContainer:
        c = RawContainer()
        c.add_provider(WorldTestProvider)
        return c

    with state.override(build_container):
        yield


@API.public
def maybe_provide_from(provider: RawProvider,
                       dependency: Hashable) -> Optional[DependencyValue]:
    """
    Only used to test providers.

    Utility function to test _providers that have not been registered in :py:mod:`.world`.
    The current :py:class:~.core.container.DependencyContainer` will be given as if it
    were registered. This allows to test exactly what has been returned by the provider.

    Args:
        provider: provider from which the dependency should be retrieved.
        dependency: dependency to retrieve.

    Returns:
        dependency instance as returned by the provider.
    """
    if provider.is_registered:
        raise RuntimeError("Method only intended to test provider that have not "
                           "been registered in world.")
    return provider.maybe_provide(dependency, state.current_container())
