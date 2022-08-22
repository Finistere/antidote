from __future__ import annotations

import itertools
import threading
import weakref
from contextlib import contextmanager, ExitStack
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    cast,
    ContextManager,
    Iterable,
    Iterator,
    Mapping,
    overload,
    Type,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

from typing_extensions import final, Protocol, TypeAlias

from .._internal import API, auto_detect_origin_frame, Default, Singleton
from ..core.exceptions import DoubleInjectionError, DuplicateProviderError, FrozenCatalogError
from ._debug import debug_str
from ._raw import create_public_private, current_catalog_onion, is_catalog_onion
from ._test import Factory, TestContext, TestContextIdImpl
from .data import DependencyDebug, dependencyOf, TestContextId, TestContextKind
from .provider import Provider, ProviderCatalog

if TYPE_CHECKING:
    from . import (
        AnyNoArgsCallable,
        Catalog,
        CatalogId,
        CatalogOverride,
        CatalogOverrides,
        CatalogProvidersMapping,
        PublicCatalog,
        TestContextBuilder,
    )

    Include: TypeAlias = Iterable[Union[Callable[[Catalog], object], PublicCatalog, Type[Provider]]]

AnyProvider = TypeVar("AnyProvider", bound=Provider)
T = TypeVar("T")
In = TypeVar("In", contravariant=True)
Out = TypeVar("Out", covariant=True)
Initial = TypeVar("Initial")
Result = TypeVar("Result")


@API.private
class CatalogOnion(Protocol):
    @property
    def private(self) -> CatalogOnion | None:
        ...

    @property
    def layer(self) -> CatalogOnionLayer:
        ...

    def new_provider_catalog(self) -> ProviderCatalog:
        ...

    def add_layer(
        self,
        *,
        keep_values: bool,
        keep_scope_vars: bool,
        public_test_context: TestContext,
        private_test_context: TestContext,
        exit_stack: ExitStack,
    ) -> None:
        ...


@API.private
class CatalogOnionLayer(Protocol):
    frozen: bool
    providers: tuple[Provider, ...]

    @property
    def id(self) -> CatalogId:
        ...

    @property
    def parent(self) -> CatalogOnionLayer | None:
        ...

    @property
    def onion(self) -> CatalogOnion:
        ...

    @property
    def test_context(self) -> TestContext | None:
        ...

    @property
    def children(self) -> tuple[CatalogOnion, ...]:
        ...

    def add_child(self, child: CatalogOnion) -> None:
        ...

    def maybe_debug(self, dependency: object) -> DependencyDebug | None:
        ...

    def __contains__(self, dependency: object) -> bool:
        ...

    def get(self, dependency: object, default: object) -> object:
        ...

    def register_scope_var(
        self,
        dependency: object,
        *,
        default: object = Default.sentinel,
    ) -> None:
        ...

    def update_scope_var(self, dependency: object, value: object) -> object:
        ...


@API.private
class CatalogSetupCallback(Protocol):
    def __call__(self, previous: CatalogOnionLayer, current: CatalogOnionLayer) -> None:
        ...


_unique_ids = itertools.count()


@API.private
@final
@dataclass(frozen=True, eq=False)
class AppCatalogProxy(Singleton):
    __slots__ = ()

    @property
    def __layer(self) -> CatalogOnionLayer:
        return current_catalog_onion.get().layer

    @property
    def id(self) -> CatalogId:
        return self.__layer.id

    def __str__(self) -> str:
        return str(self.__layer)

    def __repr__(self) -> str:
        return f"AppProxy@{self.__layer!r}"

    def __contains__(self, __dependency: object) -> bool:
        return dependencyOf(__dependency).wrapped in self.__layer

    def get(self, __dependency: Any, default: Any = None) -> Any:
        d = dependencyOf[Any](__dependency, default=default)
        return self.__layer.get(d.wrapped, d.default)

    def __getitem__(self, __dependency: Any) -> Any:
        d = dependencyOf[Any](__dependency)
        return self.__layer.get(d.wrapped, d.default)

    def debug(self, __obj: object, *, depth: int = -1) -> str:
        from ._debug import debug_str

        return debug_str(onion=current_catalog_onion.get(), origin=__obj, max_depth=depth)

    @property
    def is_frozen(self) -> bool:
        return self.__layer.frozen

    def raise_if_frozen(self) -> None:
        if self.__layer.frozen:
            raise FrozenCatalogError(self)


@API.private
@final
@dataclass(frozen=True, eq=False, repr=False)
class CatalogImpl:
    __slots__ = ("__weakref__", "test", "onion", "__private", "__lock")
    test: TestContextBuilder
    onion: CatalogOnion
    __private: CatalogImpl | None
    __lock: threading.RLock

    @staticmethod
    def next_id() -> int:
        return next(_unique_ids)

    @classmethod
    def create_public(cls, *, name: str) -> PublicCatalog:
        lock = threading.RLock()
        public, private = create_public_private(
            public_name=name,
            private_name=f"{name}#private",
        )
        return CatalogImpl(onion=public, private=CatalogImpl(onion=private, lock=lock), lock=lock)

    def __init__(
        self,
        *,
        onion: CatalogOnion,
        lock: threading.RLock,
        private: CatalogImpl | None = None,
    ) -> None:
        object.__setattr__(self, "onion", onion)
        object.__setattr__(self, "test", TestContextBuilderImpl(weakref.ref(self)))
        object.__setattr__(self, f"_{type(self).__name__}__private", private)
        object.__setattr__(self, f"_{type(self).__name__}__lock", lock)

    def __repr__(self) -> str:
        return f"Proxy@{self.onion.layer!r}"

    @property
    def id(self) -> CatalogId:
        return self.onion.layer.id

    @property
    def private(self) -> CatalogImpl:
        return self.__private or self

    def __contains__(self, __dependency: object) -> bool:
        return dependencyOf(__dependency).wrapped in self.onion.layer

    def get(self, __dependency: Any, default: Any = None) -> Any:
        d = dependencyOf[Any](__dependency, default=default)
        return self.onion.layer.get(d.wrapped, d.default)

    def __getitem__(self, __dependency: Any) -> Any:
        d = dependencyOf[Any](__dependency)
        return self.onion.layer.get(d.wrapped, d.default)

    def debug(self, __obj: object, *, depth: int = -1) -> str:
        return debug_str(onion=self.onion, origin=__obj, max_depth=depth)

    @property
    def providers(self) -> CatalogProvidersMapping:
        from . import CatalogProvidersMapping

        return CatalogProvidersMapping({type(p): p for p in self.onion.layer.providers})

    @property
    def is_frozen(self) -> bool:
        return self.onion.layer.frozen

    def raise_if_frozen(self) -> None:
        if self.onion.layer.frozen:
            raise FrozenCatalogError(self)

    def freeze(self) -> None:
        if self.__private is None:  # private
            raise RuntimeError("Cannot be called on private Catalog")
        self.raise_if_frozen()
        with self.__lock:
            _recursive_freeze(self.onion)

    @overload
    def include(self, __obj: Type[AnyProvider]) -> Type[AnyProvider]:
        ...

    @overload
    def include(self, __obj: Callable[[Catalog], Any] | PublicCatalog) -> None:
        ...

    def include(self, __obj: Any) -> Any:
        with self.__lock:
            self.raise_if_frozen()
            if isinstance(__obj, CatalogImpl):
                __obj = __obj.onion

            if is_catalog_onion(__obj):
                child_onion: CatalogOnion = __obj
                if child_onion.private is None:
                    raise ValueError(f"Cannot include private Catalog {__obj!r}")
                if child_onion.layer.parent is not None:
                    raise ValueError(
                        f"{child_onion.layer!r} is already included in {child_onion.layer.parent!r}"
                    )
                self.onion.layer.add_child(child_onion)
            elif isinstance(__obj, type) and issubclass(__obj, Provider):
                provider_class: Type[Provider] = __obj
                if any(provider_class == type(p) for p in self.onion.layer.providers):
                    raise DuplicateProviderError(
                        catalog=self.onion.layer, provider_class=provider_class
                    )
                self.onion.layer.providers += (
                    provider_class.create(catalog=self.onion.new_provider_catalog()),
                )
                if self.__private is not None:
                    try:
                        self.__private.include(provider_class)
                    except DuplicateProviderError:
                        pass
                return provider_class
            elif callable(__obj):
                func = cast(Callable[[CatalogImpl], None], __obj)
                func(self)
            else:
                raise TypeError(
                    f"Expected a catalog, a function a Provider subclass, " f"not a {type(__obj)!r}"
                )
            return None


def _setup_override(
    *,
    onion: CatalogOnion,
    setup_callback: CatalogSetupCallback,
    frozen: bool | None,
    keep_values: bool,
    keep_scope_vars: bool,
    test_context_id: TestContextId,
    exit_stack: ExitStack,
) -> None:
    private_onion = onion.private
    assert private_onion is not None

    public_previous = onion.layer
    private_previous = private_onion.layer

    onion.add_layer(
        keep_values=keep_values,
        keep_scope_vars=keep_scope_vars,
        public_test_context=TestContext.clone(
            public_previous.test_context, test_context_id, keep_values
        ),
        private_test_context=TestContext.clone(
            private_previous.test_context, test_context_id, keep_values
        ),
        exit_stack=exit_stack,
    )
    setup_callback(public_previous, onion.layer)
    setup_callback(private_previous, private_onion.layer)
    onion.layer.frozen = public_previous.frozen if frozen is None else frozen
    private_onion.layer.frozen = private_previous.frozen if frozen is None else frozen


def _recursive_freeze(onion: CatalogOnion) -> None:
    onion.layer.frozen = True
    private = onion.private
    if private is not None:
        _recursive_freeze(private)

    for child in onion.layer.children:
        _recursive_freeze(child)


OnionToLayerWeakRefs: TypeAlias = "dict[CatalogOnion, weakref.ReferenceType[CatalogOnionLayer]]"


@API.private
@final
@dataclass(frozen=True, eq=False)
class TestContextBuilderImpl:
    __slots__ = ("__catalog_ref",)
    __catalog_ref: weakref.ReferenceType[CatalogImpl]

    def copy(self, *, frozen: bool = True) -> ContextManager[CatalogOverrides]:
        return self.__context(TestContextKind.COPY, frozen=frozen)

    def clone(self, *, frozen: bool = True) -> ContextManager[CatalogOverrides]:
        return self.__context(TestContextKind.CLONE, frozen=frozen)

    def new(
        self, *, include: Include | Default = Default.sentinel
    ) -> ContextManager[CatalogOverrides]:
        if include is Default.sentinel:
            from ..lib import antidote_lib

            include = [antidote_lib]
        return self.__context(TestContextKind.NEW, include=include)

    def empty(self) -> ContextManager[CatalogOverrides]:
        return self.__context(TestContextKind.EMPTY)

    @contextmanager
    def __context(
        self,
        kind: TestContextKind,
        *,
        frozen: bool | None = None,
        include: Include = (),
    ) -> Iterator[CatalogOverrides]:
        # Helping MyPy
        catalog: CatalogImpl = self.__catalog_ref()  # type: ignore
        assert catalog is not None
        onion = catalog.onion
        assert onion.private is not None, "Cannot be called on private Catalog"

        origin = auto_detect_origin_frame(depth=3)
        keep_scope_vars = kind is TestContextKind.COPY or kind is TestContextKind.CLONE
        keep_values = kind is TestContextKind.COPY
        test_context_id = TestContextIdImpl(kind, f"{next(_unique_ids)}@{origin}")
        onion_to_layer_ref: OnionToLayerWeakRefs = {}

        exit_stack = ExitStack()
        try:
            if kind is TestContextKind.EMPTY:
                assert not include

                def callback(previous: CatalogOnionLayer, current: CatalogOnionLayer) -> None:
                    pass

            elif kind is TestContextKind.NEW:

                def callback(previous: CatalogOnionLayer, current: CatalogOnionLayer) -> None:
                    # Only applied on public layer
                    if current is catalog.onion.layer:
                        for e in include:
                            catalog.include(e)

            else:
                assert not include

                def callback(previous: CatalogOnionLayer, current: CatalogOnionLayer) -> None:
                    current.providers = tuple(
                        provider.unsafe_copy() for provider in previous.providers
                    )

                    for child_onion in previous.children:
                        assert child_onion.private is not None
                        _setup_override(
                            onion=child_onion,
                            setup_callback=callback,
                            frozen=frozen,
                            keep_scope_vars=keep_scope_vars,
                            keep_values=keep_values,
                            test_context_id=test_context_id,
                            exit_stack=exit_stack,
                        )
                        onion_to_layer_ref[child_onion] = weakref.ref(child_onion.layer)
                        onion_to_layer_ref[child_onion.private] = weakref.ref(
                            child_onion.private.layer
                        )
                        current.add_child(child_onion)

            _setup_override(
                onion=onion,
                setup_callback=callback,
                frozen=frozen,
                keep_scope_vars=keep_scope_vars,
                keep_values=keep_values,
                test_context_id=test_context_id,
                exit_stack=exit_stack,
            )
            public_ref = weakref.ref(onion.layer)
            onion_to_layer_ref[onion] = public_ref
            onion_to_layer_ref[onion.private] = weakref.ref(onion.private.layer)
            yield CatalogOverrideImpl(catalog, public_ref, onion_to_layer_ref)
        finally:
            exit_stack.close()


@API.private
@final
@dataclass(frozen=True, eq=False)
class CatalogOverrideImpl:
    __slots__ = (
        "__catalog",
        "__layer_ref",
        "__onion_to_layer_ref",
    )
    __catalog: CatalogImpl
    __layer_ref: weakref.ReferenceType[CatalogOnionLayer]
    __onion_to_layer_ref: OnionToLayerWeakRefs | None

    def of(self, catalog: Catalog) -> CatalogOverride:
        assert self.__onion_to_layer_ref is not None, "Current instance is not a CatalogOverrides"
        if not isinstance(catalog, CatalogImpl):
            raise TypeError(f"catalog must be a Catalog, not a {type(catalog)!r}")
        try:
            layer_ref = self.__onion_to_layer_ref[catalog.onion]
        except KeyError:
            raise KeyError(f"{catalog!r} has no test context (anymore)!")
        return CatalogOverrideImpl(catalog, layer_ref, None)

    @property
    def __test_context(self) -> TestContext:
        layer = self.__layer_ref()
        if layer is None:
            raise RuntimeError("Invalid test context")
        if self.__catalog.onion.layer is not layer:
            raise RuntimeError("Current test context is not the latest one.")
        test_context = layer.test_context
        assert test_context is not None
        return test_context

    def __setitem__(self, __dependency: object, __value: object) -> None:
        tc = self.__test_context
        tc.tombstones.discard(__dependency)
        tc.singletons[__dependency] = __value

    def __delitem__(self, __dependency: object) -> None:
        tc = self.__test_context
        tc.tombstones.add(__dependency)
        tc.singletons.pop(__dependency, None)
        tc.factories.pop(__dependency, None)

    @overload
    def update(self, _: Mapping[Any, object] | Iterable[tuple[object, object]]) -> None:
        ...

    @overload
    def update(self, **kwargs: object) -> None:
        ...

    def update(self, *args: object, **kwargs: object) -> None:
        if len(args) > 1 or (args and kwargs):
            raise TypeError(
                "update() expects either a dictionary or iterable of key values "
                "or keyword arguments."
            )
        if args:
            __dependencies: Any = dict(cast(Any, args[0]))
        else:
            __dependencies = kwargs

        tc = self.__test_context
        tc.singletons.update(__dependencies)
        tc.tombstones.difference_update(__dependencies.keys())

    def factory(
        self, __dependency: object, *, singleton: bool = False
    ) -> Callable[[AnyNoArgsCallable], AnyNoArgsCallable]:
        def decorate(func: AnyNoArgsCallable) -> AnyNoArgsCallable:
            from ._objects import inject

            try:
                func = inject(func, app_catalog=self.__catalog)
            except DoubleInjectionError:
                inject.rewire(func, app_catalog=self.__catalog)

            tc = self.__test_context
            tc.tombstones.discard(__dependency)
            tc.singletons.pop(__dependency, None)
            tc.factories[__dependency] = Factory(wrapped=func, singleton=singleton)
            return func

        return decorate
