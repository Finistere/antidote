from typing import cast, final, Generic, Hashable, Sequence, TypeVar

from .._internal import API
from .._internal.utils import FinalImmutable
from .._internal.utils.debug import debug_repr

T = TypeVar('T')


@API.public
@final
class Dependency(FinalImmutable, Generic[T]):
    """
    Used to clearly state that a value should be treated as a dependency and must
    be retrieved from Antidote. It is recommended to use it through
    :py:func:`~antidote.world.lazy` as presented:

    .. doctest:: core_Dependency

        >>> from antidote import world
        >>> world.singletons.set('dependency', 1)
        >>> world.lazy('dependency')
        Dependency(value='dependency')
        >>> # to retrieve the dependency later, you may use get()
        ... world.lazy[int]('dependency').get()
        1

    """
    __slots__ = ('value',)
    value: Hashable
    """Dependency to be retrieved"""

    def __init__(self, value: Hashable):
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

    @API.private
    def debug_repr(self) -> str:
        return f"Dependency(value={debug_repr(self.value)})"


@API.public
class DependencyDebug(FinalImmutable):
    """
    Debug information on a dependency. Used by :py:mod:`.world.debug` to provide runtime
    information for debugging.
    """
    __slots__ = ('info', 'singleton', 'wired', 'dependencies')
    info: str
    singleton: bool
    wired: Sequence
    dependencies: Sequence[Hashable]

    def __init__(self,
                 info: str,
                 *,
                 singleton: bool,
                 wired: Sequence = tuple(),
                 dependencies: Sequence[Hashable] = tuple()):
        """
        Args:
            info: Short and concise information on the dependency, just enough to identify
                clearly which one it is.
            singleton: Whether the dependency is a singleton or not.
            wired: Every class or function that may have been wired for this dependency.
            dependencies: Any transient dependency, so dependencies of this dependency.
        """
        super().__init__(info, singleton, wired, dependencies)
