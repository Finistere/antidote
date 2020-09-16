import inspect
from typing import TypeVar

from . import singletons, test
from .._internal import API, state
from .._internal.utils.world import WorldGet, WorldLazy
from ..core import DependencyProvider

# Creates the global container
state.init()

P = TypeVar('P', bound=type)
T = TypeVar('T')

# public
get = WorldGet()
"""
Used to retrieve a dependency from Antidote. A type hint can be provided and the result
will cast to match it. It follows the same philosophy as mypy and will NOT enforce it
with a check.

Returns:
    Retrieves given dependency or raises a :py:exc:`~.exceptions.DependencyNotFoundError`

.. doctest::
    
    >>> from antidote import world, register
    >>> world.singletons.set('dep', 1)
    >>> world.get('dep')
    1
    >>> x = world.get[int]('dep')  # mypy will treat x as a int
    ... x
    1
    >>> @register
    ... class Dummy:
    ...     pass
    >>> # To avoid repetition, if a type hint is provided but no argument, it
    ... # will retrieve the type hint itself. 
    ... world.get[Dummy]()
    Dummy

"""
lazy = WorldLazy()
"""
Used to retrieves lazily a dependency. A type hint can be provided and the retrieved
instance will be cast to match it. It follows the same philosophy as mypy and will NOT 
enforce it with a check.

Returns:
    Dependency: wrapped dependency.

.. doctest::
    
    >>> from antidote import world, register
    >>> world.singletons.set('dep', 1)
    >>> dep = world.lazy('dep')
    Dependency(value='dep')
    >>> dep.get()
    1
    >>> x = world.lazy[int]('dep').get()  # mypy will treat x as a int
    ... x
    1
    >>> @register
    ... class Dummy:
    ...     pass
    >>> # To avoid repetition, if a type hint is provided but no argument, it
    ... # will retrieve the type hint itself.
    ... world.lazy[Dummy]().get()
    Dummy

"""


@API.public
def provider(p: P) -> P:
    """
    Class decorator used to register a new
    :py:class:`~.core.provider.DependencyProvider`.
    """
    if inspect.isclass(p) and issubclass(p, DependencyProvider):
        state.get_container().register_provider(p)
        return p

    raise TypeError(f"Provider must be a subclass of "
                    f"RawDependencyProvider, not {p}")


@API.public
def freeze():
    """
    Freezes Antidote. No additional dependencies can be added and singletons
    cannot be changed anymore. Registered singleton dependencies that have not yet
    been instantiated will not be impacted.

    It can be used to ensure that at runtime, once everything is initialized, nothing
    may be changed anymore.

    .. doctest::

        >>> from antidote import world
        >>> world.freeze()
        >>> world.singletons.set('dependency', 1)
        FrozenWorldError
    """
    state.get_container().freeze()
