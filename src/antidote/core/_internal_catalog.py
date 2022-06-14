from __future__ import annotations

import threading
import weakref
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from dataclasses import dataclass
from typing import Callable, cast, Iterator, NewType, Sequence, Tuple, TYPE_CHECKING, TypeVar

from typing_extensions import final, ParamSpec

from .._internal import API, debug_repr, Default
from .._internal.typing import Function
from ..core.exceptions import (
    DependencyDefinitionError,
    DependencyNotFoundError,
    DuplicateDependencyError,
    DuplicateProviderError,
    FrozenCatalogError,
    UndefinedScopeVarError,
)
from .data import CatalogId, DependencyDebug, LifeTime
from .provider import Provider

if TYPE_CHECKING:
    from ._catalog import OverridableCatalogBuilder
    from ._override import OverridableInternalCatalog, Overrides

P = ParamSpec("P")
T = TypeVar("T")
NotFoundType = NewType("NotFoundType", object)
NotFoundSentinel = NotFoundType(object())
current_context: ContextVar[ProvideContextImpl] = ContextVar("current_context")


@API.private
@final
@dataclass(frozen=True, eq=False)
class ProvidedDependencyImpl:
    __slots__ = (
        "scope_vars",
        "value",
        "cache",
    )
    scope_vars: list[ScopeVarCache]
    value: object
    cache: Cache | NotFoundType

    def __init__(self) -> None:
        object.__setattr__(self, "scope_vars", [])
        object.__setattr__(self, "value", NotFoundSentinel)
        object.__setattr__(self, "cache", NotFoundSentinel)

    def set_value(
        self,
        value: T,
        *,
        lifetime: LifeTime | None,
        callback: Callable[[], T] | None = None,
    ) -> None:
        if self.value is not NotFoundSentinel or self.cache is not NotFoundSentinel:
            raise DependencyDefinitionError("Cannot define twice a dependency value")

        object.__setattr__(self, "value", value)
        if lifetime is LifeTime.TRANSIENT:
            if callback is None:
                return
            cache: object = TransientCache(callback=callback)
        elif lifetime is LifeTime.SCOPED:
            if not callable(callback):
                raise DependencyDefinitionError("Callback must be provided for a bound dependency")
            if not self.scope_vars:
                raise DependencyDefinitionError(
                    "No scope vars were detected. "
                    "Consider defining a singleton or transient dependency instead."
                )
            cache = ScopedCache(
                value=value,
                callback=callback,
                scope_vars_vtime=[(dep, dep.vtime) for dep in self.scope_vars],
            )
        elif lifetime is LifeTime.SINGLETON:
            if self.scope_vars:
                raise DependencyDefinitionError(
                    "Singletons cannot depend on any scope var or scoped dependency, "
                    "directly or not."
                )
            cache = value
        else:
            raise TypeError(f"lifetime must be a Scope instance, not a {type(lifetime)!r}")

        object.__setattr__(self, "cache", cache)


@API.private
@final
@dataclass(frozen=True, eq=False)
class ProvideContextImpl:
    __slots__ = ("stack", "release_stack")
    stack: list[ProvidedDependencyImpl]
    release_stack: list[Callable[[], None]]

    def __init__(self) -> None:
        object.__setattr__(self, "stack", [])
        object.__setattr__(self, "release_stack", [])

    def acquire(self, lock: threading.RLock) -> None:
        lock.acquire()
        self.release_stack.append(lock.release)

    def release(self) -> None:
        for release in reversed(self.release_stack):
            release()

    @contextmanager
    def instantiating(self, __dependency: object) -> Iterator[ProvidedDependencyImpl]:
        """
        Context Manager which has to be used when instantiating the
        dependency to keep track of the dependency path.

        When a cycle is detected, a DependencyCycleError is raised.
        """
        provided = ProvidedDependencyImpl()
        self.stack.append(provided)
        try:
            yield provided
        finally:
            self.stack.pop()
            if self.stack:
                self.stack[-1].scope_vars.extend(provided.scope_vars)


@API.private
def _copy_cache(
    *, original: dict[object, object], keep_values: bool, keep_scope_vars: bool
) -> dict[object, object]:
    assert keep_values or keep_scope_vars
    sv_copies: dict[ScopeVarCache, ScopeVarCache] = {}
    cache: dict[object, object] = {}

    if keep_values:
        for dependency, value in original.items():
            if not isinstance(value, Cache):
                cache[dependency] = value
            elif isinstance(value, ScopedCache):
                scope_vars_vtime: list[tuple[ScopeVarCache, int]] = []
                for sv, vtime in value.scope_vars_vtime:
                    try:
                        copy = sv_copies[sv]
                    # Shouldn't be possible anymore with dict being ordered by default.
                    except KeyError:  # pragma: no cover
                        copy = sv.copy(keep_value=keep_values)
                        sv_copies[sv] = copy
                    scope_vars_vtime.append((copy, vtime))

                cache[dependency] = ScopedCache(
                    value=value.value, callback=value.callback, scope_vars_vtime=scope_vars_vtime
                )
            if keep_scope_vars and isinstance(value, ScopeVarCache):
                cache[dependency] = sv_copies.setdefault(value, value.copy(keep_value=keep_values))
    else:
        for dependency, value in original.items():
            if isinstance(value, ScopeVarCache):
                cache[dependency] = value.copy(keep_value=keep_values)

    return cache


@API.private
@final
class InternalCatalog:
    def __init__(self, *, catalog_id: CatalogId) -> None:
        # Lock used to prevent multiple threads from overriding with different catalogs.
        # It does not ensure that overrides are taken into account in a thread-safe manner by
        # other threads.
        self.__id = catalog_id
        self.__frozen = False
        self.__override_lock = threading.RLock()
        self.__registration_lock = threading.RLock()
        # Securing both the stack AND the cache.
        self.__cache_lock = threading.RLock()
        self.__cache_vtime = -1 << 32
        self.__cache: dict[object, object] = {}

        self.__public: InternalCatalog | None = None
        self.__private: InternalCatalog | None = None
        self.__test_override: OverridableInternalCatalog | None = None
        self.__providers: tuple[Provider, ...] = cast(Tuple[Provider], tuple())
        self.__parent: Function[[], InternalCatalog | None] = lambda: None
        self.__children: tuple[InternalCatalog, ...] = cast(Tuple[InternalCatalog], tuple())

    @classmethod
    def create_public(cls, *, public_name: str, private_name: str) -> InternalCatalog:
        public = InternalCatalog(catalog_id=CatalogId(name=public_name))
        private = public.build_twin(id=public.id)
        # Change private family id to a different one.
        private.__id = CatalogId(name=private_name)
        public.__private = private
        private.__public = public
        return public

    def build_twin(
        self, *, id: CatalogId, keep_values: bool = False, keep_scope_vars: bool = False
    ) -> InternalCatalog:
        assert id.name == self.id.name
        catalog = InternalCatalog(catalog_id=id)
        # Keep the same cache lock for public/private pair which avoids deadlocks. For test
        # environments it doesn't really matter.
        catalog.__cache_lock = self.__cache_lock
        # Keep same override lock for public/private pair and test environment making it clearer
        # what is used when.
        catalog.__override_lock = self.__override_lock
        # Not really useful, but might as well be consistent.
        catalog.__registration_lock = self.__registration_lock
        # Keep the same frozen state when creating twins in test contexts
        catalog.__frozen = self.__frozen
        # Keeping link to private/public counterpart
        if self.__private is not None:
            catalog.__private = self.__private
        if self.__public is not None:
            catalog.__public = self.__public

        if keep_values or keep_scope_vars:
            with self.__cache_lock:
                if self.__test_override is not None:
                    original_cache = self.__test_override.internal.__cache
                else:
                    original_cache = self.__cache
                catalog.__cache = _copy_cache(
                    original=original_cache,
                    keep_values=keep_values,
                    keep_scope_vars=keep_scope_vars,
                )

        return catalog

    def __str__(self) -> str:
        providers = "[" + ", ".join(type(p).__name__ for p in self.providers) + "]"
        if self.__private is None:
            return f"PrivateCatalog(id={self.id}, providers={providers})"
        return f"Catalog(id={self.id}, providers={providers})"

    def __repr__(self) -> str:
        providers = "[" + ", ".join(type(p).__name__ for p in self.providers) + "]"
        return f"Internal(id={self.id}, providers={providers}, public={self.__private is not None})"

    @property
    def parent(self) -> InternalCatalog | None:
        return self.__parent()  # pragma: no cover

    @parent.setter
    def parent(self, value: InternalCatalog) -> None:
        with self.__registration_lock:
            assert self.__public is None, "Private Catalog cannot be a child of another Catalog."
            p = self.__parent()
            if p is not None:
                raise ValueError(f"{self} has already a parent: {p}")
            self.__parent = weakref.ref(value)

    @property
    def private(self) -> InternalCatalog:
        return self.__private or self

    @property
    def id(self) -> CatalogId:
        # not __override_lock thread-safe, but not worth the cost.
        if self.__test_override is not None:
            return self.__test_override.internal.id
        return self.__id

    @contextmanager
    def override_with(
        self, builder: OverridableCatalogBuilder, *, frozen: bool | None = None
    ) -> Iterator[tuple[Overrides, Overrides]]:
        assert self.__private is not None
        with self.__override_with(builder, frozen=frozen):
            assert self.__test_override is not None and self.__private.__test_override is not None
            yield self.__test_override.overrides, self.__private.__test_override.overrides

    @contextmanager
    def __override_with(
        self, builder: OverridableCatalogBuilder, *, frozen: bool | None = None
    ) -> Iterator[None]:
        with self.__override_lock:
            previous: OverridableInternalCatalog | None = self.__test_override
            try:
                # Ensuring atomic operation for copy & clone
                with self.__cache_lock, self.__registration_lock:
                    if previous is not None:
                        # Preventing any new changes to overrides and freezing it
                        with previous.overrides.lock:
                            catalog_override = builder(self, previous.overrides)
                            previous.overrides.frozen_by = catalog_override.internal.id
                    else:
                        catalog_override = builder(self, None)
                    if frozen is not None:
                        catalog_override.internal.__frozen = frozen
                    self.__test_override = catalog_override

                if self.__private is not None:
                    with self.__private.__override_with(builder, frozen=frozen):
                        yield
                else:
                    yield

            finally:
                if previous is not None:
                    previous.overrides.frozen_by = None
                self.__test_override = previous

    @property
    def providers(self) -> Sequence[Provider]:
        # not __override_lock thread-safe, but not worth the cost.
        if self.__test_override is not None:
            return self.__test_override.internal.providers
        return self.__providers

    @property
    def children(self) -> Sequence[InternalCatalog]:
        # not __override_lock thread-safe, but not worth the cost.
        if self.__test_override is not None:
            return self.__test_override.internal.children
        return self.__children

    @property
    def is_frozen(self) -> bool:
        # not __override_lock thread-safe, but not worth the cost.
        if self.__test_override is not None:
            return self.__test_override.internal.is_frozen

        return self.__frozen

    def freeze(self, *, ignore_already_frozen: bool = False) -> None:
        # not __override_lock thread-safe, but not worth the cost.
        if self.__test_override is not None:
            return self.__test_override.internal.freeze(ignore_already_frozen=ignore_already_frozen)

        if self.__frozen and not ignore_already_frozen:
            raise FrozenCatalogError(self)

        with self.__registration_lock:
            self.__frozen = True
            if self.__private is not None:
                self.__private.freeze(ignore_already_frozen=True)

            for child in self.__children:
                child.freeze(ignore_already_frozen=True)

    def add_provider(self, provider: Provider) -> None:
        # not __override_lock thread-safe, but not worth the cost.
        if self.__test_override is not None:
            return self.__test_override.internal.add_provider(provider)

        with self.__registration_lock:
            if self.is_frozen:
                raise FrozenCatalogError(self)
            assert isinstance(provider, Provider)
            if any(type(provider) == type(p) for p in self.__providers):
                raise DuplicateProviderError(catalog=self, provider_class=type(provider))
            self.__providers += (provider,)

    def add_child(self, catalog: InternalCatalog) -> None:
        # not __override_lock thread-safe, but not worth the cost.
        if self.__test_override is not None:
            return self.__test_override.internal.add_child(catalog)

        assert isinstance(catalog, InternalCatalog)
        assert catalog.__public is None and catalog.__private is not None
        with self.__registration_lock:
            if self.is_frozen:
                raise FrozenCatalogError(self)
            self.__children += (catalog,)

    def maybe_debug(self, dependency: object) -> DependencyDebug | None:
        # not __override_lock thread-safe, but not worth the cost.
        if self.__test_override is not None:
            return self.__test_override.maybe_debug(dependency)

        cache = self.__cache.get(dependency, NotFoundSentinel)
        if isinstance(cache, ScopeVarCache):
            return DependencyDebug(description=debug_repr(dependency), lifetime=None)

        for provider in self.__providers:
            debug = provider.maybe_debug(dependency)
            if debug is None:
                continue
            elif isinstance(debug, DependencyDebug):
                return debug
            else:
                raise TypeError(
                    f"Unsupported maybe_debug output {debug!r} fromprovider {provider!r}"
                )

        if self.__public is not None:
            debug = self.__public.maybe_debug(dependency)
            if debug is not None:
                return debug

        for child in self.__children:
            debug = child.maybe_debug(dependency)
            if debug is not None:
                return debug
        return None

    def can_provide(self, dependency: object) -> bool:
        # not __override_lock thread-safe, but not worth the cost.
        if self.__test_override is not None:
            return self.__test_override.can_provide(dependency)

        return (
            dependency in self.__cache
            or any(p.can_provide(dependency) for p in self.__providers)
            or (self.__public is not None and self.__public.can_provide(dependency))
            or any(c.can_provide(dependency) for c in self.__children)
        )

    def get(self, dependency: object, default: object = Default.sentinel) -> object:
        return copy_context().run(self.__get, dependency, default)

    def __get(self, dependency: object, default: object) -> object:
        with self.current_context() as context:
            value = self.provide(dependency, default, context)
            if value is NotFoundSentinel:
                raise DependencyNotFoundError(dependency, catalog=self)
            return value

    @contextmanager
    def current_context(self) -> Iterator[ProvideContextImpl]:
        context: ProvideContextImpl | None = current_context.get(None)
        if context is None:
            context = ProvideContextImpl()
            token = current_context.set(context)
            try:
                yield context
            finally:
                current_context.reset(token)
                context.release()
        else:
            yield context

    def provide(self, dependency: object, default: object, context: ProvideContextImpl) -> object:
        # not __override_lock thread-safe, but not worth the cost.
        if self.__test_override is not None:
            return self.__test_override.provide(dependency, default, context)

        cache_vtime = self.__cache_vtime
        cache = self.__cache.get(dependency, NotFoundSentinel)
        if cache is NotFoundSentinel:
            context.acquire(self.__cache_lock)
            if cache_vtime != self.__cache_vtime:
                cache = self.__cache.get(dependency, NotFoundSentinel)
            if cache is NotFoundSentinel:
                with context.instantiating(dependency) as provided:
                    for provider in self.__providers:
                        provider.unsafe_maybe_provide(dependency, provided)
                        if provided.value is not NotFoundSentinel:
                            if provided.cache is not NotFoundSentinel:
                                self.__cache[dependency] = provided.cache
                                self.__cache_vtime += 1
                            return provided.value

                if self.__public is not None:
                    c_result = self.__public.provide(dependency, default, context)
                    if c_result is not NotFoundSentinel:
                        return c_result

                for child in self.__children:
                    c_result = child.provide(dependency, default, context)
                    if c_result is not NotFoundSentinel:
                        return c_result

                return default if default is not Default.sentinel else NotFoundSentinel

        if isinstance(cache, Cache):
            with context.instantiating(dependency) as provided:
                if isinstance(cache, TransientCache):
                    return cache.callback()
                elif isinstance(cache, ScopedCache):
                    context.acquire(self.__cache_lock)
                    if any(dep.vtime > vtime for dep, vtime in cache.scope_vars_vtime):
                        object.__setattr__(cache, "value", cache.callback())
                        object.__setattr__(
                            cache,
                            "scope_vars_vtime",
                            [(dep, dep.vtime) for dep in provided.scope_vars],
                        )
                    else:
                        provided.scope_vars.extend(dep for dep, _ in cache.scope_vars_vtime)
                    return cache.value
                else:
                    assert isinstance(cache, ScopeVarCache)
                    context.acquire(self.__cache_lock)
                    if cache.value is NotFoundSentinel:
                        raise UndefinedScopeVarError(dependency)
                    provided.scope_vars.append(cache)
                    return cache.value

        return cache  # Either a singleton or NotFoundSentinel

    def register_scope_var(
        self,
        dependency: object,
        *,
        default: object = Default.sentinel,
    ) -> None:
        # not __override_lock thread-safe, but not worth the cost.
        if self.__test_override is not None:
            return self.__test_override.internal.register_scope_var(dependency, default=default)

        if self.is_frozen:
            raise FrozenCatalogError(self)

        cache = ScopeVarCache(default=default)
        if self.__cache.setdefault(dependency, cache) is not cache:
            raise DuplicateDependencyError(dependency)

    def update_scope_var(self, dependency: object, value: object) -> object:
        # not __override_lock thread-safe, but not worth the cost.
        if self.__test_override is not None:
            return self.__test_override.internal.update_scope_var(dependency, value)

        cache = self.__cache.get(dependency, NotFoundSentinel)
        if cache is NotFoundSentinel:  # can happen with world.test.empty()
            raise DependencyNotFoundError(dependency, catalog=self)

        assert isinstance(cache, ScopeVarCache)
        with self.__cache_lock:
            old_value = cache.value
            cache.value = value
            cache.vtime += 1
        return old_value


@API.private
class Cache:
    __slots__ = ()


@API.private
@final
@dataclass(eq=False)
class ScopeVarCache(Cache):
    __slots__ = ("vtime", "default", "value")
    vtime: int
    default: object
    value: object

    def __init__(self, *, default: object) -> None:
        self.vtime = -1 << 32
        self.default = default
        if self.default is Default.sentinel:
            self.value = NotFoundSentinel
        else:
            self.value = default

    def copy(self, *, keep_value: bool) -> ScopeVarCache:
        out = ScopeVarCache(default=self.default)
        if keep_value:
            out.value = self.value
            out.vtime = self.vtime
        return out


@API.private
@final
@dataclass(frozen=True, eq=False)
class TransientCache(Cache):
    __slots__ = ("callback",)
    callback: Callable[[], object]


@API.private
@final
@dataclass(frozen=True, eq=False)
class ScopedCache(Cache):
    __slots__ = ("value", "scope_vars_vtime", "callback")
    value: object
    scope_vars_vtime: Sequence[tuple[ScopeVarCache, int]]
    callback: Callable[[], object]
