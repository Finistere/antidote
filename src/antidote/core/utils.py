from typing import Hashable, Optional, Sequence

from .container import Scope
from .._compatibility.typing import final
from .._internal import API
from .._internal.utils import FinalImmutable


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
