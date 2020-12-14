from typing import Dict, Hashable, overload, Type, TypeVar, Union

from .._internal import API
from .._internal.state import init
from .._internal.utils.world import WorldGet, WorldLazy
from ..core.container import RawProvider

# Create the global container
init()

__sentinel = object()

# API.public
get = WorldGet()
get.__doc__ = """
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
lazy.__doc__ = """
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

P = TypeVar('P', bound=Type[RawProvider])


@API.public
def provider(p: P) -> P:
    """
    Class decorator used to register a new
    :py:class:`~.core.provider.Provider`.

    .. doctest:: world_provider

        >>> from antidote import world
        >>> from antidote.core import Provider
        >>> @world.provider
        ... class MyProvider(Provider):
        ...     '''Implementation missing'''

    Args:
        p: Provider class

    Returns:
        The same class, unmodified.

    """
    import inspect
    from .._internal import state
    from ..core.container import RawProvider

    if inspect.isclass(p) and issubclass(p, RawProvider):
        state.get_container().add_provider(p)
        return p

    raise TypeError(f"Provider must be a subclass of "
                    f"RawProvider, not {p}")


@API.public
def freeze() -> None:
    """
    Freezes Antidote. No additional dependencies can be added and singletons
    cannot be changed anymore. Registered singleton dependencies that have not yet
    been instantiated will not be impacted.

    It can be used to ensure that at runtime, once everything is initialized, nothing
    may be changed anymore.

    .. doctest:: world_freeze

        >>> from antidote import world
        >>> world.freeze()
        >>> world.singletons.add('dependency', 1)
        Traceback (most recent call last):
        ...
        FrozenWorldError

    """

    from .._internal import state
    state.get_container().freeze()


@overload
def add(dependency: Hashable, value: object) -> None: ...  # noqa: E704


@overload
def add(dependency: Dict[Hashable, object]) -> None: ...  # noqa: E704


@API.public
def add(dependency: Union[Dict[Hashable, object], Hashable],
        value: object = __sentinel) -> None:
    """
    Declare one or multiple singleton dependencies with its associated instance.

    .. doctest:: world_singletons_add

        >>> from antidote import world
        >>> world.singletons.add("test", 1)
        >>> world.get[int]("test")
        1
        >>> world.singletons.add({'host': 'example.com', 'port': 80})
        >>> world.get[str]("host")
        'example.com'

    Args:
        dependency: Singleton to declare, must be hashable. If a dict is provided, it'll
            be treated as a dictionary of singletons to add.
        value: Associated value for the dependency.

    """
    from .._internal import state
    if value is __sentinel:
        if isinstance(dependency, dict):
            state.get_container().add_singletons(dependency)
        else:
            raise TypeError("If only a single argument is provided, "
                            "it must be a dictionary of singletons.")
    else:
        if isinstance(dependency, dict):
            raise TypeError("A dictionary cannot be used as a key.")
        state.get_container().add_singletons({dependency: value})


@API.experimental
def debug(dependency: Hashable, *, depth: int = -1) -> str:
    """
    To help you debug issues you may encounter with your injections, this will provide
    a tree representing all the dependencies that will be retrieved by Antidote when
    instantiating the specified dependency. It will also show whether those are singletons
    or if there are any cyclic dependencies.

    If the specified dependency is a wired class, the wired methods will also be
    presented.

    .. doctest:: world_debug

        >>> from antidote import world
        >>> world.singletons.add("test", 1)
        >>> print(world.debug('test'))
        Singleton 'test' -> 1
        <BLANKLINE>

    .. note::

        It will NOT instantiate any dependencies, hence with :py:func:`.implementation`
        for example it won't run the function to determine which implementation must be
        used.

    Args:
        dependency: Root of the dependency tree.
        depth: Maximum depth of the result tree. Defaults to -1 which implies not limit.

    Returns:

    """
    from .._internal.state import get_container
    from .._internal.utils.debug import tree_debug_info

    return tree_debug_info(get_container(), dependency, depth)
