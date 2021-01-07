from typing import cast, Generic, Hashable, Optional, Sequence, TypeVar

from .container import Scope
from .._compatibility.typing import final
from .._internal import API
from .._internal.utils import FinalImmutable, Immutable
from .._internal.utils.debug import debug_repr
from .._internal.utils.immutable import ImmutableGenericMeta

T = TypeVar('T')


@API.public
@final
class Dependency(Immutable, Generic[T], metaclass=ImmutableGenericMeta):
    """
    Used to clearly state that a value should be treated as a dependency and must
    be retrieved from Antidote. It is recommended to use it through
    :py:func:`~antidote.world.lazy` as presented:

    .. doctest:: core_Dependency

        >>> from antidote import world
        >>> world.singletons.add('dependency', 1)
        >>> world.lazy('dependency')
        Dependency(value='dependency')
        >>> # to retrieve the dependency later, you may use get()
        ... world.lazy[int]('dependency').get()
        1

    """
    __slots__ = ('value',)
    value: Hashable
    """Dependency to be retrieved"""

    def __init__(self, value: Hashable) -> None:
        """
        Args:
            value: actual dependency to be retrieved later.
        """
        super().__init__(value=value)

    def get(self) -> T:
        """
        Returns:
            dependency instance retrieved from :py:mod:`~antidote.world`.
        """
        from antidote import world
        return cast(T, world.get(self.value))

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, Dependency)
                and (self.value is other.value or self.value == other.value))

    @API.private
    def __antidote_debug_repr__(self) -> str:
        return f"Dependency(value={debug_repr(self.value)})"


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
                 info: str,
                 *,
                 scope: Optional[Scope] = None,
                 wired: Sequence[object] = tuple(),
                 dependencies: Sequence[Hashable] = tuple()):
        """
        Args:
            info: Short and concise information on the dependency, just enough to identify
                clearly which one it is.
            singleton: Whether the dependency is a singleton or not.
            wired: Every class or function that may have been wired for this dependency.
            dependencies: Any transient dependency, so dependencies of this dependency.
        """
        super().__init__(info, scope, wired, dependencies)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, DependencyDebug) \
               and self.info == other.info \
               and self.scope == other.scope \
               and self.wired == other.wired \
               and self.dependencies == other.dependencies  # noqa: E126
