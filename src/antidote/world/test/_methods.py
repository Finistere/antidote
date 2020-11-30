from contextlib import contextmanager
from typing import Any, Callable, Hashable, Optional, overload, TypeVar, Union

from ..._internal import API, state
from ...core.container import (DependencyInstance, OverridableRawContainer, RawContainer,
                               RawProvider)


@API.public
@contextmanager
def clone(*, keep_singletons: bool = False, overridable: bool = False):
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
    if overridable:
        with state.override(lambda c: OverridableRawContainer.build(c, keep_singletons)):
            yield
    else:
        with state.override(lambda c: c.clone(keep_singletons=keep_singletons)):
            yield


@API.public
@contextmanager
def new(*, default_providers: bool = False):
    """
    Creates a new container void of any dependencies.

    Args:
        default_providers: Whether the default providers should be used. If not
            a new container with the same providers as before is created. Defaults to
            False.

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
    if default_providers:
        from ..._internal.utils.world import new_container
        with state.override(lambda _: new_container()):
            yield
    else:
        with state.override(lambda c: c.clone(keep_singletons=False,
                                              clone_providers=False)):
            yield


###############################
# Utilities to test providers #
###############################

@API.public
@contextmanager
def empty():
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
    return provider.maybe_provide(dependency, state.get_container())


__sentinel = object()


@overload
def singleton(dependency: Hashable, value) -> None: ...  # noqa: E704


@overload
def singleton(dependency: dict) -> None: ...  # noqa: E704


@API.public
def singleton(dependency: Union[dict, Hashable], value=__sentinel) -> None:
    """
    Override one or multiple dependencies with one/multiple singletons.

    .. doctest:: world_test_override_singleton

        >>> from antidote import world
        >>> world.singletons.add("test", 1)
        >>> world.get[int]("test")
        1
        >>> with world.test.clone(overridable=True):
        ...     world.test.override.singleton("test", 2)
        ...     world.test.override.singleton({'test': 2})
        ...     world.get[int]("test")
        2
        >>> # Overrides works only within the test world.
        ... world.get[int]("test")
        1

    Args:
        dependency: Singleton to declare, must be hashable. If a dict is provided, it'll
            be treated as a dictionary of singletons to add.
        value: Associated value for the dependency.

    """
    if value is __sentinel:
        if isinstance(dependency, dict):
            state.get_overridable_container().override_singletons(dependency)
        else:
            raise TypeError("If only a single argument is provided, "
                            "it must be a dictionary of singletons.")
    else:
        state.get_overridable_container().override_singletons({dependency: value})


F = TypeVar('F', bound=Callable[..., Any])


@API.public
def factory(dependency: Hashable, *, singleton: bool = False) -> Callable[[F], F]:
    """
    Override a dependency with the result of a factory. To be used as a function
    decorator. The result of the underlying function, the factory, will be used as the
    associated value of the dependency.

    .. doctest:: world_test_override_factory

        >>> from antidote import world
        >>> world.singletons.add("test", 1)
        >>> world.get[int]("test")
        1
        >>> with world.test.clone(overridable=True):
        ...     @world.test.override.factory('test', singleton=True)
        ...     def test():
        ...         return 2
        ...     world.get[int]("test")
        2
        >>> # Overrides works only within the test world.
        ... world.get[int]("test")
        1

    Args:
        dependency: Dependency to override.
        singleton: Whether the output returned by the factory should be treated as a
            singleton or not. If so, the factory will only be called once.

    .. note::

        As all override work as a single layer on top of the usual dependencies, if the
        dependency is already overridden as a singleton, the factory won't be called.
        Overrides done with a provider also have a higher priority. See
        :py:mod:`.world.test.override`.

    Returns:
        The decorated function, unchanged.
    """
    def decorate(f: 'Callable[..., Any]'):
        state.get_overridable_container().override_factory(dependency,
                                                           factory=f,
                                                           singleton=singleton)
        return f

    return decorate


P = TypeVar('P', bound=Callable[[Any], Optional[DependencyInstance]])


@API.public
def provider(p: P) -> P:
    """
    Function decorator used to declare a simplified provider to override some
    dependencies. The function will be called for each dependency and should
    return :py:class:`.core.DependencyInstance` if it can be provided or :py:obj:`None`
    if not.

    .. doctest:: world_test_override_provider

        >>> from antidote import world
        >>> from antidote.core import DependencyInstance
        >>> world.singletons.add("test", 1)
        >>> world.get[int]("test")
        1
        >>> with world.test.clone(overridable=True):
        ...     @world.test.override.provider
        ...     def test(dependency):
        ...         if dependency == 'test':
        ...             return DependencyInstance(2, singleton=True)
        ...     world.get[int]("test")
        2
        >>> # Overrides works only within the test world.
        ... world.get[int]("test")
        1

    .. note::

        As all override work as a single layer on top of the usual dependencies, singleton
        overrides won't pass through the provider. See :py:mod:`.world.test.override`.

    .. warning::

        Currently, provider overrides won't show in :py:func:`.world.debug`.

    Args:
        p: provider function.

    Returns:
        the decorated function, unchanged.
    """
    state.get_overridable_container().override_provider(p)
    return p
