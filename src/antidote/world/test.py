from contextlib import contextmanager

from .._internal import state
from .._internal.utils import API
from ..core import DependencyContainer


@API.public
@contextmanager
def clone(keep_singletons=False):
    """
    Clone current Antidote state (singletons & providers) into a new container. It should
    be used when you need to rely on existing dependencies defined in your source code.
    Otherwise consider using :py:func:`.new`.

    You're safe to:
     - add / delete a singleton
     - modify the dependency associated to a singleton
     - register new dependencies

    .. doctest::

        >>> from antidote import world, register
        >>> from antidote.exceptions import DependencyNotFoundError
        >>> world.singletons.set("test", 1)
        >>> class Service:
        ...     pass
        >>> with world.test.clone():
        ...     assert world.get("test") == 1
        ...     world.singletons.set("test", 10)
        ...     assert world.get("test") == 10
        ...     register(Service)
        ...     assert isinstance(world.get(Service), Service)
        >>> world.get("test")
        1
        >>> try:
        ...     world.get(Service)
        ...     assert False
        ... except DependencyNotFoundError:
        ...     pass

    """
    with state.override(lambda c: c.clone(keep_singletons=keep_singletons)):
        yield


@API.public
@contextmanager
def empty():
    """
    Creates an empty container. No initial provider are set up. This is useful to test one
    or several providers in isolation.
    """
    with state.override(lambda _: DependencyContainer()):
        yield


@API.public
@contextmanager
def new():
    """
    Creates a new container with all default providers used by Antidote, a clean slate.
    """
    from .._internal.defaults import new_container
    with state.override(lambda _: new_container()):
        yield
