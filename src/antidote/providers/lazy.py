from __future__ import annotations

from typing import final, Hashable, Optional

from .._internal import API
from .._internal.utils import FinalImmutable
from ..core import DependencyContainer, DependencyInstance, StatelessDependencyProvider


@API.private
class Lazy:
    def lazy_get(self, container: DependencyContainer) -> DependencyInstance:
        raise NotImplementedError()  # pragma: no cover


@API.private
@final
class FastLazyMethod(FinalImmutable, Lazy):
    __slots__ = ('dependency', 'method_name', 'value')

    def lazy_get(self, container: DependencyContainer) -> DependencyInstance:
        return DependencyInstance(
            getattr(container.get(self.dependency), self.method_name)(self.value),
            singleton=True
        )


@API.private
@final
class LazyProvider(StatelessDependencyProvider):
    def provide(self, dependency: Hashable, container: DependencyContainer
                ) -> Optional[DependencyInstance]:
        if isinstance(dependency, Lazy):
            return dependency.lazy_get(container)
