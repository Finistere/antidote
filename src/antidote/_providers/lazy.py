from typing import Hashable

from typing_extensions import final

from .._internal import API
from ..core import Container, DependencyDebug, DependencyValue, StatelessProvider
from ..core.exceptions import DebugNotAvailableError


@API.private
class Lazy:
    def __antidote_debug_info__(self) -> DependencyDebug:
        raise DebugNotAvailableError()

    def __antidote_provide__(self, container: Container) -> DependencyValue:
        raise NotImplementedError()  # pragma: no cover


@API.private
@final
class LazyProvider(StatelessProvider[Lazy]):
    def exists(self, dependency: Hashable) -> bool:
        return isinstance(dependency, Lazy)

    def debug(self, dependency: Lazy) -> DependencyDebug:
        return dependency.__antidote_debug_info__()

    def provide(self, dependency: Lazy, container: Container
                ) -> DependencyValue:
        return dependency.__antidote_provide__(container)
