from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

from ... import DuplicateDependencyError
from ..._internal import API, debug_repr
from ...core import DependencyDebug, LifeTime, ProvidedDependency, Provider, ReadOnlyCatalog

C = TypeVar("C", bound=type)


@API.private
@dataclass(frozen=True, eq=False)
class FactoryProvider(Provider):
    __slots__ = ("__factories",)
    __factories: dict[object, tuple[LifeTime | None, Callable[[], object]]]

    def __init__(
        self,
        *,
        catalog: ReadOnlyCatalog,
        factories: dict[object, tuple[LifeTime | None, Callable[[], object]]] | None = None,
    ) -> None:
        super().__init__(catalog=catalog)
        object.__setattr__(self, f"_{type(self).__name__}__factories", factories or dict())

    def can_provide(self, dependency: object) -> bool:
        return dependency in self.__factories

    def unsafe_copy(self) -> FactoryProvider:
        return FactoryProvider(catalog=self._catalog, factories=self.__factories.copy())

    def maybe_debug(self, dependency: object) -> DependencyDebug | None:
        try:
            lifetime, factory = self.__factories[dependency]
        except KeyError:
            return None
        return DependencyDebug(
            description=debug_repr(dependency), lifetime=lifetime, wired=[factory]
        )

    def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
        try:
            lifetime, factory = self.__factories[dependency]
        except KeyError:
            return

        out.set_value(factory(), lifetime=lifetime, callback=factory)

    def register(
        self, *, dependency: object, lifetime: LifeTime | None, factory: Callable[[], object]
    ) -> None:
        registration = (lifetime, factory)
        if self.__factories.setdefault(dependency, registration) is not registration:
            raise DuplicateDependencyError(f"Dependency {dependency!r} was already registered.")

    def pop(self, dependency: object) -> tuple[LifeTime | None, Callable[[], object]] | None:
        return self.__factories.pop(dependency, None)
