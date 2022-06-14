from __future__ import annotations

import itertools
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
    Optional,
    overload,
    Type,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

from typing_extensions import final, TypeAlias

from .._internal import API, auto_detect_origin_frame, Default, Singleton
from .._internal.typing import Function
from ..core.exceptions import DoubleInjectionError, DuplicateProviderError, FrozenCatalogError
from ._get import DependencyAccessorImpl
from ._internal_catalog import InternalCatalog
from ._override import OverridableInternalCatalog, Overrides, SimplifiedScopeValue
from .data import dependencyOf, TestEnv, TestEnvKind
from .provider import Provider

if TYPE_CHECKING:
    from . import (
        AnyNoArgsCallable,
        Catalog,
        CatalogId,
        CatalogOverride,
        CatalogOverrides,
        CatalogProvidersMapping,
        PublicCatalog,
        TestCatalogBuilder,
    )

    Include: TypeAlias = Iterable[Union[Callable[[Catalog], object], PublicCatalog, Type[Provider]]]

P = TypeVar("P", bound=Provider)
T = TypeVar("T")
In = TypeVar("In", contravariant=True)
Out = TypeVar("Out", covariant=True)
Initial = TypeVar("Initial")
Result = TypeVar("Result")
OverridableCatalogBuilder: TypeAlias = Callable[
    [InternalCatalog, Optional[Overrides]], OverridableInternalCatalog
]

_unique_ids = itertools.count()


@API.private
class ReadOnlyCatalogImpl(DependencyAccessorImpl):
    __slots__ = (
        "__id",
        "__source",
    )
    __id: CatalogId | None
    __source: Function[[], InternalCatalog]

    def __init__(
        self,
        *,
        source: InternalCatalog | Callable[[], InternalCatalog],
        catalog_id: CatalogId | None = None,
    ) -> None:
        object.__setattr__(self, f"_{ReadOnlyCatalogImpl.__name__}__id", catalog_id)

        if isinstance(source, InternalCatalog):
            object.__setattr__(self, f"_{ReadOnlyCatalogImpl.__name__}__source", lambda: source)

            def loader(dependency: dependencyOf[object]) -> object:
                return source.get(dependency.wrapped, dependency.default)  # type: ignore

        else:
            object.__setattr__(self, f"_{ReadOnlyCatalogImpl.__name__}__source", source)

            def loader(dependency: dependencyOf[object]) -> object:
                return source().get(dependency.wrapped, dependency.default)  # type: ignore

        super().__init__(loader=loader)

    @property
    def id(self) -> CatalogId:
        if self.__id is not None:
            return self.__id
        return self.__source().id

    def __str__(self) -> str:
        return str(self.__source())

    def __repr__(self) -> str:
        return f"Catalog@{self.__source()!r}"

    # public & private freeze together, so it works whether the source is private or not.
    @property
    def is_frozen(self) -> bool:
        return self.__source().is_frozen

    def __contains__(self, __dependency: object) -> bool:
        return self.__source().can_provide(dependencyOf(__dependency).wrapped)

    def debug(self, __obj: object, *, depth: int = -1) -> str:
        from ._debug import tree_debug_info

        return tree_debug_info(self.__source(), __obj, depth)

    def raise_if_frozen(self) -> None:
        if self.__source().is_frozen:
            raise FrozenCatalogError(self)


@API.private
@final
@dataclass(frozen=True, eq=False, repr=False)
class AppCatalog(ReadOnlyCatalogImpl, Singleton):
    def __init__(self) -> None:
        from ._wrapper import current_catalog_context

        super().__init__(source=current_catalog_context.get)


@API.private
@final
@dataclass(frozen=True, eq=False, repr=False)
class CatalogImpl(ReadOnlyCatalogImpl):
    __slots__ = ("internal", "__private", "__parent", "test")
    internal: InternalCatalog
    __private: CatalogImpl | None
    __parent: CatalogImpl | None
    test: TestCatalogBuilder

    @classmethod
    def create_public(cls, *, name: str, origin: str) -> PublicCatalog:
        unique_id = next(_unique_ids)
        public = InternalCatalog.create_public(
            public_name=f"{name}#{unique_id}@{origin}",
            private_name=f"{name}#private-{unique_id}@{origin}",
        )
        return CatalogImpl(catalog=public, private=CatalogImpl(catalog=public.private))

    @property
    def private(self) -> Catalog:
        if self.__private is not None:
            return self.__private
        return self

    @property
    def providers(self) -> CatalogProvidersMapping:
        from . import CatalogProvidersMapping

        return CatalogProvidersMapping({type(p): p for p in self.internal.providers})

    def __init__(self, *, catalog: InternalCatalog, private: CatalogImpl | None = None) -> None:
        super().__init__(source=catalog)
        object.__setattr__(self, "internal", catalog)
        object.__setattr__(self, f"_{type(self).__name__}__private", private)
        object.__setattr__(self, f"_{type(self).__name__}__parent", None)
        if private is not None:
            object.__setattr__(
                self,
                "test",
                TestCatalogBuilderImpl(self.internal),
            )

    def freeze(self) -> None:
        if self.__private is None:
            raise AttributeError("freeze() is not accessible in a private catalog.")
        self.internal.freeze()

    @overload
    def include(self, __obj: Type[P]) -> Type[P]:
        ...

    @overload
    def include(self, __obj: Callable[[Catalog], Any] | PublicCatalog) -> None:
        ...

    def include(self, __obj: Any) -> Any:
        if isinstance(__obj, CatalogImpl):
            if __obj.private is __obj:
                raise ValueError("Cannot include a private Catalog")
            # Setting atomically the parent of the child, ensuring there can be only one.
            __obj.internal.parent = self.internal
            self.internal.add_child(__obj.internal)
        elif isinstance(__obj, type) and issubclass(__obj, Provider):
            self.internal.add_provider(
                __obj.create(
                    catalog=ReadOnlyCatalogImpl(source=self.internal.private, catalog_id=self.id)
                )
            )
            if self.__private is not None:
                try:
                    self.__private.include(__obj)
                except DuplicateProviderError:
                    pass
            return __obj
        elif callable(__obj):
            __obj(self)  # type: ignore
        else:
            raise TypeError(
                f"Expected a catalog, a function a Provider subclass, " f"not a {type(__obj)!r}"
            )


@API.private
@final
@dataclass(frozen=True, eq=False)
class TestCatalogBuilderImpl:
    __slots__ = ("__internal",)
    __internal: InternalCatalog

    def copy(self, *, frozen: bool = True) -> ContextManager[CatalogOverrides]:
        return self.__context(strategy=TestEnvKind.COPY, frozen=frozen)

    def clone(self, *, frozen: bool = True) -> ContextManager[CatalogOverrides]:
        return self.__context(strategy=TestEnvKind.CLONE, frozen=frozen)

    def new(
        self, *, include: Include | Default = Default.sentinel
    ) -> ContextManager[CatalogOverrides]:
        if include is Default.sentinel:
            from ..lib import antidote_lib

            include = [antidote_lib]
        return self.__context(strategy=TestEnvKind.NEW, include=include)

    def empty(self) -> ContextManager[CatalogOverrides]:
        return self.__context(strategy=TestEnvKind.EMPTY)

    @contextmanager
    def __context(
        self,
        *,
        strategy: TestEnvKind,
        frozen: bool | None = None,
        include: Include | None = None,
    ) -> Iterator[CatalogOverrides]:
        origin = auto_detect_origin_frame(depth=3)
        catalog_to_overrides: dict[InternalCatalog, Overrides] = dict()
        with ExitStack() as stack:
            builder = self.__create_builder(
                origin=origin,
                context_stack=stack,
                catalog_to_overrides=catalog_to_overrides,
                kind=strategy,
                include=include,
            )

            with self.__internal.override_with(builder, frozen=frozen) as (
                public_overrides,
                private_overrides,
            ):
                catalog_to_overrides[self.__internal] = public_overrides
                catalog_to_overrides[self.__internal.private] = private_overrides
                yield CatalogOverridesImpl(
                    catalog_to_overrides=catalog_to_overrides, catalog=self.__internal
                )

    @staticmethod
    def __create_builder(
        *,
        origin: str,
        context_stack: ExitStack,
        catalog_to_overrides: dict[InternalCatalog, Overrides],
        kind: TestEnvKind,
        include: Include | None,
    ) -> OverridableCatalogBuilder:
        env: TestEnv = TestEnvImpl(kind=kind, suffix=f"{next(_unique_ids)}@{origin}")

        if kind is TestEnvKind.EMPTY:
            assert include is None

            def build_empty(
                original: InternalCatalog, prev_overrides: Overrides | None
            ) -> OverridableInternalCatalog:
                return OverridableInternalCatalog(
                    internal=original.build_twin(id=original.id.within_env(env)),
                    overrides=Overrides(),
                )

            return build_empty

        elif kind is TestEnvKind.NEW:
            assert include is not None

            def build_new(
                original: InternalCatalog, prev_overrides: Overrides | None
            ) -> OverridableInternalCatalog:
                internal = original.build_twin(id=original.id.within_env(env))
                catalog = CatalogImpl(catalog=internal)
                for e in include or tuple():  # for mypy
                    catalog.include(e)
                return OverridableInternalCatalog(
                    internal=internal,
                    overrides=Overrides(),
                )

            return build_new
        else:
            assert include is None
            copy = kind is TestEnvKind.COPY

        def build(
            original: InternalCatalog, prev_overrides: Overrides | None
        ) -> OverridableInternalCatalog:
            catalog = OverridableInternalCatalog(
                internal=original.build_twin(
                    id=original.id.within_env(env), keep_values=copy, keep_scope_vars=True
                ),
                overrides=(
                    prev_overrides.clone(copy=copy) if prev_overrides is not None else Overrides()
                ),
            )
            for provider in original.providers:
                catalog.internal.add_provider(provider.unsafe_copy())

            for child in original.children:
                public_overrides, private_overrides = context_stack.enter_context(
                    child.override_with(build)
                )
                catalog_to_overrides[child] = public_overrides
                catalog_to_overrides[child.private] = private_overrides
                catalog.internal.add_child(child)

            return catalog

        return build


@API.private
@final
@dataclass(frozen=True)
class TestEnvImpl:
    kind: TestEnvKind
    suffix: str

    def __str__(self) -> str:
        return f"{self.kind.name}{self.suffix}"


@API.private
@dataclass(frozen=True, eq=False)
class CatalogOverrideImpl:
    __slots__ = ("__internal", "__overrides")
    __internal: InternalCatalog
    __overrides: Overrides

    @contextmanager
    def __safe_overrides(self) -> Iterator[Overrides]:
        with self.__overrides.lock:
            if self.__overrides.frozen_by is not None:
                raise RuntimeError(
                    f"Cannot change overrides, "
                    f"they're overridden by new context of "
                    f"{self.__overrides.frozen_by}"
                )
            yield self.__overrides

    def __setitem__(self, __dependency: object, __value: object) -> None:
        with self.__safe_overrides() as overrides:
            if __dependency in overrides.tombstones:
                overrides.tombstones.remove(__dependency)
            overrides.singletons[__dependency] = __value

    def __delitem__(self, __dependency: object) -> None:
        with self.__safe_overrides() as overrides:
            overrides.tombstones.add(__dependency)
            if __dependency in overrides.singletons:
                del overrides.singletons[__dependency]
            if __dependency in overrides.factories:
                del overrides.factories[__dependency]

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
            __dependencies: dict[Any, object] = dict(cast(Any, args[0]))
        else:
            __dependencies = kwargs

        with self.__safe_overrides() as overrides:
            overrides.singletons.update(__dependencies)
            overrides.tombstones.difference_update(__dependencies.keys())

    def factory(
        self, __dependency: object, *, singleton: bool = False
    ) -> Callable[[AnyNoArgsCallable], AnyNoArgsCallable]:
        def decorate(func: AnyNoArgsCallable) -> AnyNoArgsCallable:
            from ._inject import InjectorImpl

            inject = InjectorImpl()

            try:
                func = inject(func, catalog=self.__internal)
            except DoubleInjectionError:
                inject.rewire(func, catalog=self.__internal)

            with self.__safe_overrides() as overrides:
                if __dependency in overrides.tombstones:
                    overrides.tombstones.remove(__dependency)
                overrides.factories[__dependency] = SimplifiedScopeValue(
                    wrapped=func, singleton=singleton
                )
            return func

        return decorate


@API.private
@final
@dataclass(frozen=True, eq=False)
class CatalogOverridesImpl(CatalogOverrideImpl):
    __slots__ = ("__catalog_to_overrides",)
    __catalog_to_overrides: dict[InternalCatalog, Overrides]

    def __init__(
        self, *, catalog_to_overrides: dict[InternalCatalog, Overrides], catalog: InternalCatalog
    ) -> None:
        super().__init__(catalog, catalog_to_overrides[catalog])
        object.__setattr__(
            self, f"_{type(self).__name__}__catalog_to_overrides", catalog_to_overrides
        )

    def of(self, catalog: Catalog) -> CatalogOverride:
        if not isinstance(catalog, CatalogImpl):
            raise TypeError(f"catalog must be a Catalog, not a {type(catalog)!r}")
        try:
            overrides = self.__catalog_to_overrides[catalog.internal]
        except KeyError:
            raise KeyError(f"{catalog!r} wasn't overridden in this test environment!")
        return CatalogOverrideImpl(catalog.internal, overrides)
