from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Generic, TYPE_CHECKING, TypeVar

from typing_extensions import final

from .._internal import API, debug_repr, Default
from ._internal_catalog import InternalCatalog, NotFoundSentinel, ProvideContextImpl
from .data import CatalogId, DependencyDebug, LifeTime

if TYPE_CHECKING:
    pass

T = TypeVar("T")


@dataclass(frozen=True, eq=True)
class SimplifiedScopeValue(Generic[T]):
    wrapped: T
    singleton: bool


@API.private
@final
@dataclass
class Overrides:
    frozen_by: CatalogId | None = None
    tombstones: set[object] = field(default_factory=set)
    singletons: dict[object, object] = field(default_factory=dict)
    factories: dict[object, SimplifiedScopeValue[Callable[[], object]]] = field(
        default_factory=dict
    )
    lock: threading.RLock = field(default_factory=threading.RLock)

    def clone(self, *, copy: bool) -> Overrides:
        return Overrides(
            tombstones=self.tombstones.copy(),
            singletons=self.singletons.copy() if copy else {},
            factories=self.factories.copy(),
            lock=self.lock,
        )


@API.private
@final
@dataclass(frozen=True, eq=False)
class OverridableInternalCatalog:
    __slots__ = ("internal", "overrides")
    internal: InternalCatalog
    overrides: Overrides

    def provide(self, __dependency: object, default: object, context: ProvideContextImpl) -> object:
        if __dependency in self.overrides.tombstones:
            return default if default is not Default.sentinel else NotFoundSentinel

        try:
            return self.overrides.singletons[__dependency]
        except KeyError:
            pass

        try:
            factory = self.overrides.factories[__dependency]
        except KeyError:
            pass
        else:
            with context.instantiating(__dependency):
                value = factory.wrapped()
            if factory.singleton:
                with self.overrides.lock:
                    self.overrides.singletons[__dependency] = value
            return value

        return self.internal.provide(__dependency, default, context)

    def can_provide(self, __dependency: object) -> bool:
        if __dependency in self.overrides.tombstones:
            return False

        return (
            __dependency in self.overrides.singletons
            or __dependency in self.overrides.factories
            or self.internal.can_provide(__dependency)
        )

    def maybe_debug(self, __dependency: object) -> DependencyDebug | None:
        if __dependency in self.overrides.tombstones:
            return None

        try:
            value = self.overrides.singletons[__dependency]
        except KeyError:
            pass
        else:
            return DependencyDebug(
                description=f"Override/Singleton: {debug_repr(__dependency)} -> {value!r}",
                lifetime=LifeTime.SINGLETON,
            )
        try:
            wrapped_factory = self.overrides.factories[__dependency]
        except KeyError:
            pass
        else:
            return DependencyDebug(
                description=f"Override/Factory: {debug_repr(__dependency)} "
                f"-> {debug_repr(wrapped_factory.wrapped)}",
                lifetime=LifeTime.SINGLETON if wrapped_factory.singleton else None,
            )

        return self.internal.maybe_debug(__dependency)
