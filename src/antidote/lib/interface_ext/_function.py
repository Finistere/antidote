from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, cast, Generic, Optional, Sequence

from typing_extensions import final, ParamSpec

from ..._internal import API, debug_repr_call, EMPTY_DICT, EMPTY_TUPLE, wraps_frozen
from ..._internal.typing import Out
from ...core import (
    Catalog,
    CatalogId,
    Dependency,
    DependencyDebug,
    LifeTime,
    ProvidedDependency,
    ProviderCatalog,
)
from ..lazy_ext import LazyFunction
from ..lazy_ext._provider import LazyDependency
from ._internal import create_constraints, ImplementationQuery
from .predicate import PredicateConstraint

__all__ = ["InterfaceWrapper", "FunctionInterfaceImpl", "LazyInterfaceImpl"]

P = ParamSpec("P")


@API.private
class InterfaceWrapper:
    __slots__ = ()


@API.private
@final
@dataclass(frozen=True, eq=False)
class FunctionInterfaceImpl(InterfaceWrapper, Generic[P, Out]):
    __slots__ = ("__single", "wrapped", "catalog", "__dict__")
    wrapped: Callable[P, Out]
    catalog: Catalog
    catalog_id: CatalogId
    __single: ImplementationQuery[Callable[P, Out]]

    def __init__(self, *, wrapped: Callable[P, Out], catalog: Catalog) -> None:
        object.__setattr__(self, "wrapped", wrapped)
        object.__setattr__(self, "catalog", catalog)
        object.__setattr__(self, "catalog_id", catalog.id)
        object.__setattr__(self, f"_{type(self).__name__}__single", self.single())
        wraps_frozen(wrapped, signature=inspect.signature(wrapped))(self)

    def __antidote_dependency_hint__(self) -> Callable[P, Out]:
        return cast(Callable[P, Out], self.__single)

    def single(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Dependency[Callable[P, Out]]:
        return ImplementationQuery[Callable[P, Out]](
            interface=self.wrapped,
            constraints=create_constraints(
                *constraints, qualified_by=qualified_by, qualified_by_one_of=qualified_by_one_of
            ),
        )

    def all(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Dependency[Sequence[Callable[P, Out]]]:
        from ._internal import create_constraints

        return ImplementationQuery[Sequence[Callable[P, Out]]](  # type: ignore
            interface=self.wrapped,
            constraints=create_constraints(
                *constraints, qualified_by=qualified_by, qualified_by_one_of=qualified_by_one_of
            ),
            all=True,
        )

    def __repr__(self) -> str:
        return f"FunctionInterface({self.wrapped!r}, catalog_id={self.catalog_id})"


@API.private
@final
@dataclass(frozen=True, eq=False)
class LazyInterfaceImpl(InterfaceWrapper, Generic[P, Out]):
    __slots__ = ("__single", "wrapped", "catalog", "catalog_id", "__dict__")
    wrapped: Callable[P, Out]
    catalog: Catalog
    catalog_id: CatalogId
    __signature: inspect.Signature
    __single: Callable[P, Dependency[Out]]

    def __init__(self, *, wrapped: Callable[P, Out], catalog: Catalog) -> None:
        object.__setattr__(self, "wrapped", wrapped)
        object.__setattr__(self, "catalog", catalog)
        object.__setattr__(self, "catalog_id", catalog.id)
        object.__setattr__(self, f"_{type(self).__name__}__signature", inspect.signature(wrapped))
        object.__setattr__(self, f"_{type(self).__name__}__single", self.single())
        wraps_frozen(wrapped, signature=self.__signature)(self)

    def single(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Callable[P, Dependency[Out]]:
        from ._internal import create_constraints

        query: ImplementationQuery[LazyFunction[..., Out]] = ImplementationQuery[Any](
            interface=self.wrapped,
            constraints=create_constraints(
                *constraints, qualified_by=qualified_by, qualified_by_one_of=qualified_by_one_of
            ),
        )

        def f(*args: P.args, **kwargs: P.kwargs) -> Dependency[Out]:
            bound = self.__signature.bind(*args, **kwargs)
            return LazySingleDependency(
                query=query,
                args=bound.args or EMPTY_TUPLE,
                kwargs=bound.kwargs or EMPTY_DICT,
                catalog_id=self.catalog_id,
            )

        return f

    def all(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Callable[P, Dependency[Sequence[Out]]]:
        from ._internal import create_constraints

        query: ImplementationQuery[Sequence[LazyFunction[..., Out]]] = ImplementationQuery[Any](
            interface=self.wrapped,
            constraints=create_constraints(
                *constraints, qualified_by=qualified_by, qualified_by_one_of=qualified_by_one_of
            ),
            all=True,
        )

        def f(*args: P.args, **kwargs: P.kwargs) -> Dependency[Sequence[Out]]:
            bound = self.__signature.bind(*args, **kwargs)
            return LazyAllDependency(
                query=query,
                args=bound.args or EMPTY_TUPLE,
                kwargs=bound.kwargs or EMPTY_DICT,
                catalog_id=self.catalog_id,
            )

        return f

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Dependency[Out]:
        return self.__single(*args, **kwargs)

    def __repr__(self) -> str:
        return f"LazyInterface({self.wrapped!r}, catalog_id={self.catalog_id})"


@API.private
@final
@dataclass(frozen=True, eq=False)
class LazySingleDependency(LazyDependency, Generic[Out]):
    __slots__ = ("query", "args", "kwargs", "catalog_id")
    query: ImplementationQuery[LazyFunction[..., Out]]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    catalog_id: CatalogId

    def __antidote_debug__(self) -> DependencyDebug:
        _repr = debug_repr_call(
            cast(Callable[..., object], self.query.interface), self.args, self.kwargs
        )
        return DependencyDebug(
            description=f"<lazy-single> {_repr}",
            dependencies=[self.query],
            lifetime="transient",
        )

    def __antidote_unsafe_provide__(
        self, catalog: ProviderCatalog, out: ProvidedDependency
    ) -> None:
        out.set_value(
            value=catalog[catalog[self.query](*self.args, **self.kwargs)],
            lifetime=LifeTime.TRANSIENT,
        )

    def __antidote_dependency_hint__(self) -> Out:
        return cast(Out, self)


@API.private
@final
@dataclass(frozen=True, eq=False)
class LazyAllDependency(LazyDependency, Generic[Out]):
    __slots__ = ("query", "args", "kwargs", "catalog_id")
    query: ImplementationQuery[Sequence[LazyFunction[..., Out]]]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    catalog_id: CatalogId

    def __antidote_debug__(self) -> DependencyDebug:
        _repr = debug_repr_call(
            cast(Callable[..., object], self.query.interface), self.args, self.kwargs
        )
        return DependencyDebug(
            description=f"<lazy-all> {_repr}",
            dependencies=[self.query],
            lifetime="transient",
        )

    def __antidote_unsafe_provide__(
        self, catalog: ProviderCatalog, out: ProvidedDependency
    ) -> None:
        out.set_value(
            value=[catalog[f(*self.args, **self.kwargs)] for f in catalog[self.query]],
            lifetime=LifeTime.TRANSIENT,
        )

    def __antidote_dependency_hint__(self) -> Sequence[Out]:
        return cast(Sequence[Out], self)
