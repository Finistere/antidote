from typing import Generic, Hashable, Optional, Sequence, TypeVar, cast

from .container import Scope
from .._compatibility.typing import final
from .._internal import API
from .._internal.utils import FinalImmutable, Immutable
from .._internal.utils.immutable import ImmutableGenericMeta

T = TypeVar('T')
_SENTINEL = object()


@API.public
@final
class LazyDependency(Immutable, Generic[T], metaclass=ImmutableGenericMeta):
    """
    Recommended usage is to usage :py:func:`..world.lazy`:

    .. doctest:: core_utils_dependency

        >>> from antidote import world, Service
        >>> class MyService(Service):
        ...     pass
        >>> port = world.lazy[MyService]()
        >>> port.get()
        <MyService ...>

    """
    __slots__ = ('unwrapped',)
    unwrapped: Hashable
    """Actual dependency to be retrieved"""

    def __init__(self, __dependency: Hashable) -> None:
        """
        Args:
            __dependency: actual dependency to be retrieved.
        """
        super().__init__(unwrapped=__dependency)

    def get(self) -> T:
        """
        Returns:
            dependency value retrieved from :py:mod:`~..world`.
        """
        from antidote import world
        return cast(T, world.get(self.unwrapped))

    def __hash__(self) -> int:
        return hash(self.unwrapped)

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, LazyDependency)
                and (self.unwrapped is other.unwrapped
                     or self.unwrapped == other.unwrapped))


@API.public
@final
class DependencyDebug(FinalImmutable):
    """
    Debug information on a dependency. Used by :py:mod:`.world.debug` to provide runtime
    information for debugging.
    """
    __slots__ = ('info', 'scope', 'wired', 'dependencies')
    info: str
    scope: Optional[Scope]
    wired: Sequence[object]
    dependencies: Sequence[Hashable]

    def __init__(self,
                 __info: str,
                 *,
                 scope: Optional[Scope] = None,
                 wired: Sequence[object] = tuple(),
                 dependencies: Sequence[Hashable] = tuple()):
        """
        Args:
            __info: Short and concise information on the dependency, just enough to
                identify clearly which one it is.
            scope: Scope of the dependency.
            wired: Every class or function that may have been wired for this dependency.
            dependencies: Any transient dependency, so dependencies of this dependency.
        """
        super().__init__(__info, scope, wired, dependencies)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, DependencyDebug) \
               and self.info == other.info \
               and self.scope == other.scope \
               and self.wired == other.wired \
               and self.dependencies == other.dependencies  # noqa: E126
