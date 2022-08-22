from __future__ import annotations

import threading
import weakref
from contextlib import ExitStack
from contextvars import ContextVar, copy_context
from dataclasses import dataclass, field
from typing import Callable, Sequence, TYPE_CHECKING, TypeVar

from typing_extensions import final

from ..._internal import API, debug_repr, Default
from ..._internal.typing import Function
from ..data import CatalogId, DependencyDebug, LifeTime, TestContextId
from ..exceptions import (
    DependencyDefinitionError,
    DependencyNotFoundError,
    DuplicateDependencyError,
    FrozenCatalogError,
    UndefinedScopeVarError,
)

if TYPE_CHECKING:
    from .._catalog import CatalogOnion, CatalogOnionLayer
    from .._test import TestContext
    from ..provider import Provider, ProviderCatalog

__all__ = ["CatalogOnionImpl", "current_context", "NotFoundSentinel", "ProvideContext"]

current_context: ContextVar[ProvideContext] = ContextVar("current_context")

T = TypeVar("T")
NotFoundSentinel = object()
ChildNotFoundSentinel = object()


@dataclass(frozen=True)
class CacheOverrideBuilder:
    original: dict[object, object]
    keep_values: bool
    old_to_override: dict[ScopeVarCache, ScopeVarCache] = field(default_factory=dict)
    finalizers: list[Callable[[], None]] = field(default_factory=list)

    @classmethod
    def copy(cls, original: dict[object, object], keep_values: bool) -> dict[object, object]:
        return CacheOverrideBuilder(
            original=original,
            keep_values=keep_values,
        ).build()

    def build(self) -> dict[object, object]:
        result: dict[object, object] = {}
        copy_scope_var = self.__copy_var

        if self.keep_values:
            for dependency, value in self.original.items():
                if not isinstance(value, Cache):
                    result[dependency] = value
                elif isinstance(value, ScopedCache):
                    result[dependency] = ScopedCache(
                        value=value.value,
                        callback=value.callback,
                        scope_vars_vtime=[
                            (copy_scope_var(scope_var), vtime)
                            for scope_var, vtime in value.scope_vars_vtime
                        ],
                    )
                else:
                    assert isinstance(value, ScopeVarCache)
                    result[dependency] = copy_scope_var(value)
        else:
            for dependency, value in self.original.items():
                if isinstance(value, ScopeVarCache):
                    result[dependency] = copy_scope_var(value)

        return result

    def __copy_var(self, scope_var: ScopeVarCache) -> ScopeVarCache:
        try:
            return self.old_to_override[scope_var]
        except KeyError:
            assert isinstance(scope_var, ScopeGlobalVarCache)
            copy = ScopeGlobalVarCache(default=scope_var.default)
            if self.keep_values:
                copy.value = scope_var.value
                copy.vtime = scope_var.vtime
            return self.old_to_override.setdefault(scope_var, copy)


@API.private
@final
@dataclass(eq=False)
class ProvideContext:
    __slots__ = (
        "scope_vars_stack",
        "release_stack",
        "current_value",
        "current_cache",
    )
    scope_vars_stack: list[list[ScopeVarCache]]
    release_stack: list[Callable[[], None]]
    current_value: object
    current_cache: object

    def __init__(self) -> None:
        self.scope_vars_stack = []
        self.release_stack = []
        self.current_value = NotFoundSentinel
        self.current_cache = NotFoundSentinel

    def acquire(self, lock: threading.RLock) -> None:
        lock.acquire()
        self.release_stack.append(lock.release)

    def release(self) -> None:
        for release in reversed(self.release_stack):
            release()

    def stack_push(self) -> None:
        assert (
            self.current_value is NotFoundSentinel
        ), "Context is dirty! After using set_value, the catalog cannot be used anymore!"
        self.scope_vars_stack.append([])

    def stack_pop(self) -> None:
        self.current_value = NotFoundSentinel
        stack = self.scope_vars_stack
        scope_vars = stack.pop()
        if stack:
            stack[-1].extend(scope_vars)

    def set_value(
        self,
        value: T,
        *,
        lifetime: LifeTime,
        callback: Callable[[], T] | None = None,
    ) -> None:
        if self.current_value is not NotFoundSentinel or self.current_cache is not NotFoundSentinel:
            raise DependencyDefinitionError("Cannot define twice a dependency value")

        self.current_value = value
        if lifetime is LifeTime.TRANSIENT:
            if callback is not None:
                self.current_cache = TransientCache(callback=callback)
        elif lifetime is LifeTime.SCOPED:
            if not callable(callback):
                raise DependencyDefinitionError("Callback must be provided for a bound dependency")
            if not self.scope_vars_stack[-1]:
                raise DependencyDefinitionError(
                    "No scope vars were detected. "
                    "Consider defining a singleton or transient dependency instead."
                )
            self.current_cache = ScopedCache(
                value=value,
                callback=callback,
                scope_vars_vtime=[(dep, dep.vtime) for dep in self.scope_vars_stack[-1]],
            )
        elif lifetime is LifeTime.SINGLETON:
            if self.scope_vars_stack[-1]:
                raise DependencyDefinitionError(
                    "Singletons cannot depend on any scope var or scoped dependency, "
                    "directly or not."
                )
            self.current_cache = value
        else:
            raise TypeError(f"lifetime must be a Scope instance, not a {type(lifetime)!r}")


@API.private
@dataclass(frozen=True, eq=False)
class ProviderCatalogImpl:
    __slots__ = (
        "__id",
        "__onion",
    )
    __id: CatalogId
    __onion: CatalogOnionImpl

    @property
    def id(self) -> CatalogId:
        return self.__id

    def __repr__(self) -> str:
        return f"ProviderCatalog(id={self.__id}, catalog={self.__onion.layer!r})"

    def __contains__(self, dependency: object) -> bool:
        return dependency in self.__onion.layer

    def __getitem__(self, dependency: object) -> object:
        return self.__onion.layer.get(dependency, NotFoundSentinel)

    def get(self, dependency: object, default: object = None) -> object:
        return self.__onion.layer.get(dependency, default)

    @property
    def is_frozen(self) -> bool:
        return self.__onion.layer.frozen

    def raise_if_frozen(self) -> None:
        if self.__onion.layer.frozen:
            raise FrozenCatalogError(self)

    def debug(self, __obj: object, *, depth: int = -1) -> str:
        from .._debug import debug_str

        return debug_str(onion=self.__onion, origin=__obj, max_depth=depth)


@API.private
@final
@dataclass(frozen=True)
class CatalogOnionImpl:
    __slots__ = ("__weakref__", "name", "private", "__layers", "__layers_lock")
    name: str
    private: CatalogOnionImpl | None
    __layers: list[CatalogOnionLayerImpl]
    __layers_lock: threading.RLock

    @classmethod
    def create_public_private(
        cls, *, public_name: str, private_name: str
    ) -> tuple[CatalogOnion, CatalogOnion]:
        private = CatalogOnionImpl(name=private_name)
        public = CatalogOnionImpl(name=public_name, private=private)
        public.__layers.append(CatalogOnionLayerImpl(onion_ref=weakref.ref(public), public=None))
        private.__layers.append(
            CatalogOnionLayerImpl(onion_ref=weakref.ref(private), public=public.__layers[-1])
        )
        return public, private

    def __init__(self, *, name: str, private: CatalogOnionImpl | None = None) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "private", private)
        object.__setattr__(self, f"_{type(self).__name__}__layers", [])
        object.__setattr__(self, f"_{type(self).__name__}__layers_lock", threading.RLock())

    def __hash__(self) -> int:
        return object.__hash__(self)

    def __repr__(self) -> str:
        return f"CatalogOnion(name={self.name}, private={self.private is None})"

    def new_provider_catalog(self) -> ProviderCatalog:
        # Access to private dependencies, but the id is the real one.
        return ProviderCatalogImpl(self.layer.id, (self.private or self))

    @property
    def layer(self) -> CatalogOnionLayerImpl:
        return self.__layers[-1]

    def add_layer(
        self,
        *,
        keep_values: bool,
        keep_scope_vars: bool,
        public_test_context: TestContext,
        private_test_context: TestContext,
        exit_stack: ExitStack,
    ) -> None:
        assert self.private is not None, "Cannot be called on private CatalogOnion"
        # Ensuring no other thread modifies the layers now.
        exit_stack.enter_context(self.__layers_lock)
        previous = self.__layers[-1]
        self.__layers.append(
            previous.clone(
                keep_values=keep_values,
                keep_scope_vars=keep_scope_vars,
                test_context=public_test_context,
                public=None,
            )
        )
        private_previous = self.private.__layers[-1]
        self.private.__layers.append(
            private_previous.clone(
                keep_values=keep_values,
                keep_scope_vars=keep_scope_vars,
                test_context=private_test_context,
                public=self.__layers[-1],
            )
        )

        exit_stack.callback(self.__peel_layer)

    def __peel_layer(self) -> None:
        self.__layers.pop()
        assert self.__layers

        assert self.private is not None
        self.private.__layers.pop()
        assert self.private.__layers


@API.private
@final
@dataclass
class CatalogOnionLayerImpl:
    __slots__ = (
        "__weakref__",
        "id",
        "frozen",
        "providers",
        "__parent_ref",
        "__onion_ref",
        "__test_context",
        "__children",
        "__public",
        "__cache",
        "__vtime",
        "__lock",
    )
    frozen: bool
    providers: tuple[Provider, ...]
    id: CatalogId

    __parent_ref: Function[[], CatalogOnionLayerImpl | None]
    __onion_ref: Function[[], CatalogOnionImpl | None]
    __public: CatalogOnionLayerImpl | None
    __children: tuple[CatalogOnionImpl, ...]
    __test_context: TestContext | None
    __cache: dict[object, object]
    __vtime: int
    __lock: threading.RLock

    def clone(
        self,
        *,
        keep_values: bool,
        keep_scope_vars: bool,
        test_context: TestContext,
        public: CatalogOnionLayerImpl | None,
    ) -> CatalogOnionLayerImpl:
        if keep_scope_vars:
            cache: dict[object, object] = CacheOverrideBuilder.copy(
                original=self.__cache,
                keep_values=keep_values,
            )
        else:
            cache = {}

        return CatalogOnionLayerImpl(
            onion_ref=self.__onion_ref,
            lock=self.__lock,
            test_context=test_context,
            cache=cache,
            public=public,
        )

    def __init__(
        self,
        *,
        onion_ref: Callable[[], CatalogOnionImpl | None],
        public: CatalogOnionLayerImpl | None,
        lock: threading.RLock | None = None,
        test_context: TestContext | None = None,
        cache: dict[object, object] | None = None,
    ) -> None:
        self.providers = ()
        self.frozen = False

        self.__parent_ref = lambda: None
        self.__children = ()
        self.__vtime = 0
        self.__cache = cache if cache is not None else {}
        self.__lock = lock or threading.RLock()
        self.__test_context = test_context
        self.__onion_ref = onion_ref
        self.__public = public

        if test_context is None:
            test_context_ids: tuple[TestContextId, ...] = ()
        else:
            previous = self.onion.layer.id.test_context_ids
            if not previous:
                test_context_ids = (test_context.id,)
            else:
                tmp = list(self.onion.layer.id.test_context_ids)
                tmp.append(test_context.id)
                test_context_ids = tuple(tmp)

        self.id = CatalogId(self.onion.name, test_context_ids)

    def __repr__(self) -> str:
        attrs = [f"id={self.id}"]
        if self.providers:
            providers = "[" + ", ".join(type(p).__name__ for p in self.providers) + "]"
            attrs.append(f"providers={providers}")
        if self.__children:
            children = "[" + ",".join(map(repr, self.__children)) + "]"
            attrs.append(f"children={children}")
        return f"CatalogLayer({', '.join(attrs)})"

    @property
    def parent(self) -> CatalogOnionLayer | None:
        return self.__parent_ref()

    @property
    def onion(self) -> CatalogOnionImpl:
        onion = self.__onion_ref()
        assert onion is not None, f"Unbound layer {self!r}"
        return onion

    @property
    def test_context(self) -> TestContext | None:
        return self.__test_context

    @property
    def children(self) -> tuple[CatalogOnion, ...]:
        return self.__children

    def add_child(self, child: CatalogOnion) -> None:
        assert (
            isinstance(child, CatalogOnionImpl)
            and child.private is not None
            and child.layer.__parent_ref() is None
        )
        child.layer.__parent_ref = weakref.ref(self)
        self.__children += (child,)

    def maybe_debug(self, dependency: object) -> DependencyDebug | None:
        if self.__test_context is not None:
            if dependency in self.__test_context.tombstones:
                return None
            out: DependencyDebug | None = self.__test_context.maybe_debug(dependency)
            if out is not None:
                return out

        for provider in self.providers:
            out = provider.maybe_debug(dependency)
            if isinstance(out, DependencyDebug):
                return out

        if isinstance(self.__cache.get(dependency, NotFoundSentinel), ScopeVarCache):
            return DependencyDebug(description=debug_repr(dependency), lifetime=None)

        if self.__public is not None:
            out = self.__public.maybe_debug(dependency)
            if out is not None:
                return out

        for child_onion in self.__children:
            out = child_onion.layer.maybe_debug(dependency)
            if out is not None:
                return out

        return None

    def __contains__(self, dependency: object) -> bool:
        test_context = self.__test_context
        if test_context is not None:
            if dependency in test_context.tombstones:
                return False
            if dependency in test_context:
                return True

        public = self.__public
        return (
            dependency in self.__cache
            or any(p.can_provide(dependency) for p in self.providers)
            or (public is not None and dependency in public)
            or any(dependency in child.layer for child in self.__children)
        )

    def get(self, dependency: object, default: object) -> object:
        return copy_context().run(self._get, dependency, default)

    def _get(self, dependency: object, default: object) -> object:
        context: ProvideContext | None = current_context.get(None)
        if context is None:
            context = ProvideContext()
            token = current_context.set(context)
            try:
                value = self.provide(dependency, default, context)
            finally:
                current_context.reset(token)
                context.release()
        else:
            value = self.provide(dependency, default, context)
        return value

    def provide(self, dependency: object, default: object, context: ProvideContext) -> object:
        test_context = self.__test_context
        if test_context is not None:
            if dependency in test_context.tombstones:
                return default
            value = test_context.singletons.get(dependency, NotFoundSentinel)
            if value is not NotFoundSentinel:
                return value
            with self.__lock:
                value = test_context.unsafe_factory_get(dependency, NotFoundSentinel)
            if value is not NotFoundSentinel:
                return value

        vtime = self.__vtime
        cached = self.__cache.get(dependency, NotFoundSentinel)
        if cached is NotFoundSentinel:
            context.acquire(self.__lock)
            if vtime != self.__vtime:
                cached = self.__cache.get(dependency, NotFoundSentinel)
            if cached is NotFoundSentinel:
                context.stack_push()
                try:
                    for provider in self.providers:
                        provider.unsafe_maybe_provide(dependency, context)
                        if context.current_value is not NotFoundSentinel:
                            if context.current_cache is not NotFoundSentinel:
                                self.__cache[dependency] = context.current_cache
                                self.__vtime += 1
                                context.current_cache = NotFoundSentinel
                            return context.current_value
                finally:
                    context.stack_pop()

                public = self.__public
                if public is not None:
                    value = public.provide(dependency, ChildNotFoundSentinel, context)
                    if value is not ChildNotFoundSentinel:
                        return value

                for child_onion in self.__children:
                    value = child_onion.layer.provide(dependency, ChildNotFoundSentinel, context)
                    if value is not ChildNotFoundSentinel:
                        return value

                if default is NotFoundSentinel:
                    raise DependencyNotFoundError(dependency, catalog=self)

                return default

        if isinstance(cached, Cache):
            context.stack_push()
            try:
                if isinstance(cached, TransientCache):
                    return cached.callback()
                elif isinstance(cached, ScopedCache):
                    context.acquire(self.__lock)
                    if any(dep.vtime > vtime for dep, vtime in cached.scope_vars_vtime):
                        object.__setattr__(cached, "value", cached.callback())
                        object.__setattr__(
                            cached,
                            "scope_vars_vtime",
                            [(dep, dep.vtime) for dep in context.scope_vars_stack[-1]],
                        )
                    else:
                        context.scope_vars_stack[-1].extend(
                            dep for dep, _ in cached.scope_vars_vtime
                        )
                    return cached.value
                else:
                    assert isinstance(cached, ScopeGlobalVarCache)
                    context.acquire(self.__lock)
                    if cached.value is NotFoundSentinel:
                        raise UndefinedScopeVarError(dependency)
                    context.scope_vars_stack[-1].append(cached)
                    return cached.value
            finally:
                context.stack_pop()

        return cached  # Either a singleton or NotFoundSentinel

    def register_scope_var(
        self,
        dependency: object,
        *,
        default: object = Default.sentinel,
    ) -> None:
        assert not self.frozen
        cache = ScopeGlobalVarCache(default=default)
        if self.__cache.setdefault(dependency, cache) is not cache:
            raise DuplicateDependencyError(dependency)

    def update_scope_var(self, dependency: object, value: object) -> object:
        cache = self.__cache.get(dependency, NotFoundSentinel)
        if cache is NotFoundSentinel:  # can happen with world.test.empty()
            raise DependencyNotFoundError(dependency, catalog=self)

        assert isinstance(cache, ScopeGlobalVarCache)
        with self.__lock:
            old_value = cache.value
            cache.value = value
            cache.vtime += 1
        return old_value


@API.private
class Cache:
    __slots__ = ()


@API.private
@final
@dataclass(frozen=True, eq=False)
class TransientCache(Cache):
    __slots__ = ("callback",)
    callback: Callable[[], object]


@API.private
class ScopeVarCache(Cache):
    __slots__ = ("vtime",)
    vtime: int


@API.private
@final
@dataclass(eq=False)
class ScopeGlobalVarCache(ScopeVarCache):
    __slots__ = ("default", "value")
    vtime: int
    default: object
    value: object

    def __init__(self, *, default: object) -> None:
        self.vtime = 0
        self.default = default
        if self.default is Default.sentinel:
            self.value = NotFoundSentinel
        else:
            self.value = default


@API.private
@final
@dataclass(frozen=True, eq=False)
class ScopedCache(Cache):
    __slots__ = ("value", "scope_vars_vtime", "callback")
    value: object
    scope_vars_vtime: Sequence[tuple[ScopeVarCache, int]]
    callback: Callable[[], object]
