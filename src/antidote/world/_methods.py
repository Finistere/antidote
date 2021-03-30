import inspect
from typing import Hashable, Type, TypeVar

from .._internal import API
from .._internal.state import current_container, init
from .._internal.world import WorldGet, WorldLazy
from ..core.container import RawProvider, Scope

# Create the global container
init()

__sentinel = object()

# API.public
get = WorldGet()
get.__doc__ = """
Used to retrieve a dependency from Antidote. A type hint can be provided and the result
will cast to match it. It follows the same philosophy as mypy and will NOT enforce it.

.. doctest:: world_get

    >>> from antidote import world, Service
    >>> class Dummy(Service):
    ...     pass
    >>> world.get(Dummy)
    <Dummy ...>
    >>> # But Mypy will only an object, not a `Dummy` instance. For this Mypy needs help:
    >>> world.get[Dummy](Dummy)  # Treated by Mypy as a Dummy
    <Dummy ...>
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
enforce it.

.. doctest:: world_lazy

    >>> from antidote import world, Service
    >>> class Dummy(Service):
    ...     pass
    >>> dep = world.lazy(Dummy)
    >>> dep.get()
    <Dummy ...>
    >>> # But Mypy will only an object, not a `Dummy` instance. For this Mypy needs help:
    >>> world.lazy[Dummy](Dummy).get()  # Treated by Mypy as a Dummy
    <Dummy ...>
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
    if not (inspect.isclass(p) and issubclass(p, RawProvider)):
        raise TypeError(f"Provider must be a subclass of "
                        f"RawProvider, not {p}")
    container = current_container()
    if any(p == type(existing_provider) for existing_provider in container.providers):
        raise ValueError(f"Provider {p} already exists")
    container.add_provider(p)
    return p


@API.public
def freeze() -> None:
    """
    Freezes Antidote. No additional dependencies or scope can be defined.

    Its primary purpose is to state explicitly in your code when all dependencies have
    been defined and to offer a bit more control on Antidote's state.

    .. doctest:: world_freeze

        >>> from antidote import world, Service
        >>> world.freeze()
        >>> class Dummy(Service):
        ...     pass
        Traceback (most recent call last):
        ...
        FrozenWorldError

    """
    current_container().freeze()


@API.experimental
def debug(dependency: Hashable, *, depth: int = -1) -> str:
    """
    To help you debug issues you may encounter with your injections, this will provide
    a tree representing all the dependencies that will be retrieved by Antidote when
    instantiating the specified dependency. It will also show whether those are singletons
    or if there are any cyclic dependencies.

    .. doctest:: world_debug

        >>> from antidote import world, Service, Provide
        >>> class Dummy(Service):
        ...     pass
        >>> class Root(Service):
        ...     def __init__(self, dummy: Provide[Dummy]):
        ...         pass
        >>> print(world.debug(Root))
        Root
        └── Dummy
        <BLANKLINE>
        Singletons have no scope markers.
        <∅> = no scope (new instance each time)
        <name> = custom scope
        <BLANKLINE>

    .. note::

        With :py:func:`.implementation`, it'll execute the function to know which
        dependency to follow.

    Args:
        dependency: Root of the dependency tree.
        depth: Maximum depth of the result tree. Defaults to -1 which implies not limit.

    Returns:

    """
    from .._internal.utils.debug import tree_debug_info

    return tree_debug_info(current_container(), dependency, depth)


def new(*, name: str) -> Scope:
    """
    Creates a new scope. See :py:class:`~.core.container.Scope` for more information on
    scopes.

    .. doctest:: world_scopes_new

        >>> from antidote import world, Service
        >>> REQUEST_SCOPE = world.scopes.new(name='request')
        >>> class Dummy(Service):
        ...     __antidote__ = Service.Conf(scope=REQUEST_SCOPE)

    Args:
        name: Friendly identifier used for debugging purposes. It must be unique.
    """
    from .._internal.state import current_container
    if not isinstance(name, str):
        raise TypeError(f"name must be a str, not {type(name)}")
    if not name:
        raise ValueError("name cannot be an empty string")
    if name in {Scope.singleton().name, Scope.sentinel().name}:
        raise ValueError(f"'{name}' is a reserved scope name.")
    container = current_container()
    if any(s.name == name for s in container.scopes):
        raise ValueError(f"A scope '{name}' already exists")
    return container.create_scope(name)


def reset(scope: Scope) -> None:
    """
    All dependencies values of the specified scope will be discarded, so invalidating the
    scope. See :py:class:`~.core.container.Scope` for more information on scopes.

    .. doctest:: world_scopes_reset

        >>> from antidote import world
        >>> REQUEST_SCOPE = world.scopes.new(name='request')
        >>> # All cached dependencies value with scope=REQUEST_SCOPE will be discarded.
        ... world.scopes.reset(REQUEST_SCOPE)

    Args:
        scope: Scope to reset.
    """
    if not isinstance(scope, Scope):
        raise TypeError(f"scope must be a Scope, not {type(scope)}.")
    if scope in {Scope.singleton(), Scope.sentinel()}:
        raise ValueError(f"Cannot reset {scope}.")
    container = current_container()
    if scope not in container.scopes:
        raise ValueError(f"Unknown scope {scope}. Only scopes created through "
                         f"world.scopes.new() are supported.")
    return container.reset_scope(scope)
