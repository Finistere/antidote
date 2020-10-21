from __future__ import annotations

from typing import final, Hashable

from .._internal import API
from .._internal.utils import FinalImmutable, debug_repr
from ..core import Container, DependencyInstance, StatelessProvider
from ..core.utils import DependencyDebug


@API.private
class Lazy:
    def debug_info(self) -> DependencyDebug:
        raise NotImplementedError()  # pragma: no cover

    def lazy_get(self, container: Container) -> DependencyInstance:
        raise NotImplementedError()  # pragma: no cover


@API.private
@final
class FastLazyMethod(FinalImmutable, Lazy):
    __slots__ = ('dependency', 'method_name', 'value')
    dependency: object
    method_name: str
    value: object

    def debug_info(self) -> DependencyDebug:
        return DependencyDebug(f"Lazy Method {self.method_name} with {self.value!r} on "
                               f"{debug_repr(self.dependency)}",
                               singleton=True,
                               dependencies=[self.dependency])

    def lazy_get(self, container: Container) -> DependencyInstance:
        return DependencyInstance(
            getattr(container.get(self.dependency), self.method_name)(self.value),
            singleton=True
        )


@API.private
@final
class LazyProvider(StatelessProvider[Lazy]):
    def exists(self, dependency: Hashable) -> bool:
        return isinstance(dependency, Lazy)

    def debug(self, dependency: Lazy) -> DependencyDebug:
        return dependency.debug_info()

    def provide(self, dependency: Lazy, container: Container
                ) -> DependencyInstance:
        return dependency.lazy_get(container)
