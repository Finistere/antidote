import inspect
from typing import Type, TypeVar

from . import debug, singletons, test
from .._internal import API, state
from .._internal.utils.world import WorldGet, WorldLazy
from ..core.container import RawProvider

# Creates the global container
state.init()

P = TypeVar('P', bound=Type[RawProvider])
T = TypeVar('T')

# API.public
get = WorldGet()
"""
Used to retrieve a dependency from Antidote. A type hint can be provided and the result
will cast to match it. It follows the same philosophy as mypy and will NOT enforce it
with a check.

Returns:
    Retrieves given dependency or raises a :py:exc:`~.exceptions.DependencyNotFoundError`

.. doctest:: world_get

    >>> from antidote import world, Service
    >>> world.singletons.add('dep', 1)
    >>> world.get('dep')
    1
    >>> # mypy will treat x as a int
    ... x = world.get[int]('dep')
    >>> class Dummy(Service):
    ...     pass
    >>> # To avoid repetition, if a type hint is provided but no argument, it
    ... # will retrieve the type hint itself.
    ... world.get[Dummy]()
    <Dummy ...>

"""

# API.public
lazy = WorldLazy()
"""
Used to retrieves lazily a dependency. A type hint can be provided and the retrieved
instance will be cast to match it. It follows the same philosophy as mypy and will NOT
enforce it with a check.

Returns:
    Dependency: wrapped dependency.

.. doctest:: world_lazy

    >>> from antidote import world, Service
    >>> world.singletons.add('dep', 1)
    >>> dep = world.lazy('dep')
    >>> dep
    Dependency(value='dep')
    >>> dep.get()
    1
    >>> # mypy will treat x as a int
    ... x = world.lazy[int]('dep').get()
    >>> class Dummy(Service):
    ...     pass
    >>> # To avoid repetition, if a type hint is provided but no argument, it
    ... # will retrieve the type hint itself.
    ... world.lazy[Dummy]().get()
    <Dummy ...>

"""


@API.public
def provider(p: P) -> P:
    """
    Class decorator used to register a new
    :py:class:`~.core.provider.Provider`.
    """
    if inspect.isclass(p) and issubclass(p, RawProvider):
        state.get_container().add_provider(p)
        return p

    raise TypeError(f"Provider must be a subclass of "
                    f"RawProvider, not {p}")


@API.public
def freeze():
    """
    Freezes Antidote. No additional dependencies can be added and singletons
    cannot be changed anymore. Registered singleton dependencies that have not yet
    been instantiated will not be impacted.

    It can be used to ensure that at runtime, once everything is initialized, nothing
    may be changed anymore.

    .. doctest:: world_freeze

        >>> from antidote import world
        >>> from antidote.exceptions import FrozenWorldError
        >>> world.freeze()
        >>> try:
        ...     world.singletons.add('dependency', 1)
        ... except FrozenWorldError:
        ...     print("Frozen world !")
        Frozen world !
    """
    state.get_container().freeze()
