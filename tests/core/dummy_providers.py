from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, overload, TypeVar

from typing_extensions import final, TypeAlias

from antidote import Dependency, LifeTime
from antidote.core import LifetimeType, ProvidedDependency, Provider, ProviderCatalog

T = TypeVar("T")
Callback: TypeAlias = "Callable[[ProviderCatalog, ProvidedDependency], object]"


@final
@dataclass(eq=False)
class DummyProvider(Provider):
    __slots__ = ("_singleton", "data")
    _singleton: bool
    data: dict[object, object]

    @property
    def catalog(self) -> ProviderCatalog:
        return self._catalog

    def __init__(
        self,
        *,
        catalog: ProviderCatalog,
        data: dict[object, object] | None = None,
        singleton: bool = True,
    ):
        super().__init__(catalog=catalog)
        object.__setattr__(self, "_singleton", singleton)
        object.__setattr__(self, "data", data or {})

    def unsafe_copy(self) -> DummyProvider:
        return DummyProvider(
            catalog=self._catalog, singleton=self._singleton, data=self.data.copy()
        )

    def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
        if dependency in self.data:
            out.set_value(
                value=self.data[dependency],
                lifetime=LifeTime.SINGLETON if self.singleton else LifeTime.TRANSIENT,
            )

    def can_provide(self, dependency: object) -> bool:
        return dependency in self.data

    @property
    def singleton(self) -> bool:
        return self._singleton


@final
@dataclass(frozen=True, eq=False)
class DummyFactoryProvider(Provider):
    __slots__ = ("_data",)
    _data: dict[object, Callable[[ProviderCatalog, ProvidedDependency], object]]

    def __init__(
        self,
        *,
        catalog: ProviderCatalog,
        data: dict[object, Callable[[ProviderCatalog, ProvidedDependency], object]] | None = None,
    ):
        super().__init__(catalog=catalog)
        object.__setattr__(self, "_data", data or {})

    def unsafe_copy(self) -> DummyFactoryProvider:
        return DummyFactoryProvider(catalog=self._catalog, data=self._data)

    def can_provide(self, dependency: object) -> bool:
        return dependency in self._data

    def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
        if dependency in self._data:
            self._data[dependency](self._catalog, out)

    def add(
        self,
        dependency: object,
        *,
        factory: Callable[[ProviderCatalog], object],
        lifetime: LifetimeType = LifeTime.SINGLETON,
    ) -> DummyFactoryProvider:
        self._data[dependency] = lambda c, out: out.set_value(
            value=factory(c), lifetime=LifeTime.of(lifetime)
        )
        return self

    @overload
    def add_raw(self) -> Callable[[Callback], Dependency[object]]:
        ...

    @overload
    def add_raw(self, dependency: object) -> Callable[[Callback], Callback]:
        ...

    def add_raw(self, dependency: object = None) -> Any:
        def decorate(callback: Callback) -> Any:
            nonlocal dependency
            dependency = callback if dependency is None else dependency
            self._data[dependency] = callback
            return callback

        return decorate
