from contextlib import contextmanager
from typing import cast, Hashable, Optional

from .._internal import API, state
from .._internal.utils.world import OverridableProviderCollection
from ..core.container import DependencyInstance, RawContainer, RawProvider


@API.public
@contextmanager
def clone(*, keep_singletons: bool = False, overridable: bool = False):
    """
    Clone current Antidote state (singletons & providers) into a new container. It should
    be used when you need to rely on existing dependencies defined in your source code.
    Otherwise consider using :py:func:`.new`.

    You're safe to:
     - add / delete a singleton
     - modify the dependency associated to a singleton
     - register new dependencies

    .. doctest::

        >>> from antidote import world, service
        >>> from antidote.exceptions import DependencyNotFoundError
        >>> world.singletons.add("test", 1)
        >>> class Service:
        ...     pass
        >>> with world.test.clone():
        ...     assert world.get("test") == 1
        ...     world.singletons.add("test", 10)
        ...     assert world.get("test") == 10
        ...     service(Service)
        ...     assert isinstance(world.get(Service), Service)
        >>> world.get("test")
        1
        >>> try:
        ...     world.get(Service)
        ...     assert False
        ... except DependencyNotFoundError:
        ...     pass

    """
    if overridable:
        def build_new_container(c: RawContainer) -> RawContainer:
            # Do not clone providers, re-create new ones.
            new_container = c.clone(keep_singletons=keep_singletons,
                                    clone_providers=False)
            # Old providers will be accessible from ProviderCollection
            new_container.add_provider(OverridableProviderCollection)
            provider_collection = cast(OverridableProviderCollection,
                                       new_container.get(OverridableProviderCollection))
            # Do not keep cached singletons
            provider_collection.set_providers([p.clone(keep_singletons_cache=False)
                                               for p in c.providers])

            return new_container

        with state.override(build_new_container):
            yield
    else:
        with state.override(lambda c: c.clone(keep_singletons=keep_singletons)):
            yield


@API.public
@contextmanager
def new():
    """
    Creates a new container void of any dependencies.
    """
    with state.override(lambda c: c.clone(keep_singletons=False, clone_providers=False)):
        yield


###############################
# Utilities to test providers #
###############################

@API.public
@contextmanager
def empty():
    """
    Creates an empty container. No initial provider are set up. This is useful to test one
    or several providers in isolation. If you're not testing provider use
    :py:func:`.new` instead.
    """
    with state.override(lambda _: RawContainer()):
        yield


@API.public
def maybe_provide_from(provider: RawProvider, dependency: Hashable
                       ) -> Optional[DependencyInstance]:
    """
    Utility function to test providers that have not been registered in :py:mod:`.world`.
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
