from contextlib import contextmanager
from typing import (Hashable, Iterator, Optional)

from ..._internal import API, state
from ...core.container import (DependencyInstance, OverridableRawContainer, RawContainer,
                               RawProvider)


@API.public
@contextmanager
def clone(*,
          keep_singletons: bool = False,
          keep_scopes: bool = False,
          overridable: bool = False
          ) -> Iterator[None]:
    """
    Clone current Antidote state (singletons & providers) into a new container. It should
    be used when you need to rely on existing dependencies defined in your source code.
    Otherwise consider using :py:func:`.new`.

    You're safe to:
     - add / delete singletons
     - override dependencies if :code:`overridable=True`
     - register new dependencies

    .. doctest:: world_test_clone

        >>> from antidote import world, Service
        >>> from antidote.exceptions import DependencyNotFoundError
        >>> world.singletons.add("test", 1)
        >>> class MyService(Service):
        ...     pass
        >>> with world.test.clone():
        ...     # By default singletons are not propagated
        ...     world.get[int]("test")
        Traceback (most recent call last):
        ...
        DependencyNotFoundError: 'test'
        >>> with world.test.clone():
        ...     # But anything else will be accessible
        ...     world.get[MyService]()
        <MyService object ...>
        >>> # You can have the singletons if wish though:
        ... with world.test.clone(keep_singletons=True):
        ...     assert world.get[int]("test") == 1
        ...     # Overriding is still impossible by default.
        ...     world.singletons.add("test", 10)
        Traceback (most recent call last):
        ...
        DuplicateDependencyError: 'test'
        >>> with world.test.clone(overridable=True, keep_singletons=True):
        ...     # Antidote will support an override once before any usage.
        ...     world.test.override.singleton("test", 10)
        ...     world.get[int]("test")
        10
        >>> # The original singleton is preserved
        ... world.get[int]("test")
        1

    Args:
        keep_singletons: Whether current singletons should be kept in the new world. Keep
            in mind that while you can add and delete singletons without worries, keeping
            singletins means that you will have the same instances. Defaults to False.
        overridable: Whether dependencies can be overriden in the new container. Note
            that you can only override dependencies *once* and only *before any usage*.
            Defaults to False.

    Returns:
        context manager within you can make your tests.

    """

    def build(c: RawContainer) -> RawContainer:
        return c.clone(keep_singletons=keep_singletons,
                       keep_scopes=keep_scopes)

    if overridable:
        def overridable_build(c: RawContainer) -> RawContainer:
            return OverridableRawContainer.from_clone(build(c))

        with state.override(overridable_build):
            yield
    else:
        with state.override(build):
            yield


@API.public
@contextmanager
def new(*, raw: bool = False) -> Iterator[None]:
    """
    Creates a new container void of any dependencies.

    Args:
        raw: If :py:obj:`True`, you'll get a new world without any  modifications. If
            :py:obj:`False`, existing scopes and providers will be present in the new
            container. But they won't have anything in them, as if you just declared
            them, contrary to :py:func:`.clone`. Defaults to :py:obj:`False`.

    .. doctest:: world_test_new

        >>> from antidote import world
        >>> world.singletons.add("test", 1)
        >>> with world.test.new():
        ...     # Current world is empty
        ...     world.get[int]("test")
        Traceback (most recent call last):
        ...
        DependencyNotFoundError: 'test'
        >>> with world.test.new():
        ...     world.singletons.add("new", 2)
        >>> # Anything done within the context manager stays there.
        ... world.get[int]("new")
        Traceback (most recent call last):
        ...
        DependencyNotFoundError: 'test'

    """
    from ..._internal.utils.world import new_container
    if raw:
        with state.override(lambda _: new_container()):
            yield
    else:
        def build(old: RawContainer) -> RawContainer:
            c = new_container(empty=True)
            for provider in old.providers:
                c.add_provider(type(provider))
            return c

        with state.override(build):
            yield


###############################
# Utilities to test providers #
###############################

@API.public
@contextmanager
def empty() -> Iterator[None]:
    """
    Only used to test providers.

    Creates an empty container. No initial provider are set up. This is useful to test one
    or several providers in isolation. If you're not testing provider use :py:func:`.new`
    instead.
    """
    with state.override(lambda _: RawContainer()):
        yield


@API.public
def maybe_provide_from(provider: RawProvider,
                       dependency: Hashable) -> Optional[DependencyInstance]:
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
