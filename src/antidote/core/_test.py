from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

from typing_extensions import final

from .._internal import API, debug_repr
from .data import DependencyDebug, LifeTime, TestContextId, TestContextKind

T = TypeVar("T")

__all__ = ["TestContext", "TestContextIdImpl"]


@API.private
@final
@dataclass(frozen=True, eq=True)
class Factory:
    __slots__ = ("wrapped", "singleton")
    wrapped: Callable[[], object]
    singleton: bool


@API.private
@final
@dataclass(frozen=True)
class TestContextIdImpl:
    __slots__ = ("kind", "name")
    kind: TestContextKind
    name: str

    def __str__(self) -> str:
        return f"{self.kind.name.lower()}#{self.name}"


@API.private
@final
@dataclass(frozen=True, eq=False)
class TestContext:
    __slots__ = ("id", "tombstones", "singletons", "factories")
    id: TestContextId
    tombstones: set[object]
    singletons: dict[object, object]
    factories: dict[object, Factory]

    @staticmethod
    def clone(original: TestContext | None, id: TestContextId, keep_values: bool) -> TestContext:
        if original is None:
            return TestContext(id, set(), {}, {})
        return TestContext(
            id,
            original.tombstones.copy(),
            original.singletons.copy() if keep_values else {},
            original.factories.copy(),
        )

    def unsafe_factory_get(self, dependency: object, default: object) -> object:
        try:
            factory = self.factories[dependency]
        except KeyError:
            pass
        else:
            if factory.singleton:
                try:
                    return self.singletons[dependency]
                except KeyError:
                    value = factory.wrapped()
                    self.singletons[dependency] = value
                    return value
            else:
                return factory.wrapped()

        return default

    def __contains__(self, dependency: object) -> bool:
        return dependency in self.singletons or dependency in self.factories

    def maybe_debug(self, dependency: object) -> DependencyDebug | None:
        try:
            value = self.singletons[dependency]
        except KeyError:
            pass
        else:
            return DependencyDebug(
                description=f"Override/Singleton: {debug_repr(dependency)} -> {value!r}",
                lifetime=LifeTime.SINGLETON,
            )
        try:
            wrapped_factory = self.factories[dependency]
        except KeyError:
            pass
        else:
            return DependencyDebug(
                description=f"Override/Factory: {debug_repr(dependency)} "
                f"-> {debug_repr(wrapped_factory.wrapped)}",
                lifetime=LifeTime.SINGLETON if wrapped_factory.singleton else None,
            )

        return None
