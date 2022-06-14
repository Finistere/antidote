from __future__ import annotations

from dataclasses import dataclass
from typing import cast, Generic, TYPE_CHECKING, TypeVar

from typing_extensions import final

from .._internal import API, auto_detect_var_name, debug_repr, Default, enforce_valid_name
from ._catalog import CatalogImpl
from ._internal_catalog import InternalCatalog, NotFoundSentinel
from .data import CatalogId, Missing

if TYPE_CHECKING:
    from . import Catalog

__all__ = ["ScopeVar", "ScopeVarToken"]

T = TypeVar("T")


@API.experimental
@final
@dataclass(frozen=True, eq=False)
class ScopeVar(Generic[T]):
    __slots__ = ("name", "catalog_id", "__internal")
    name: str
    catalog_id: CatalogId
    __internal: InternalCatalog

    def __init__(
        self,
        *,
        default: T | Default = Default.sentinel,
        name: str | Default = Default.sentinel,
        catalog: Catalog | Default = Default.sentinel,
    ) -> None:
        from ._objects import world

        if isinstance(catalog, Default):
            catalog = world

        if isinstance(name, Default):
            name = auto_detect_var_name()
        else:
            enforce_valid_name(name)

        if not isinstance(catalog, CatalogImpl):
            raise TypeError(f"catalog must be a Catalog, not a {type(catalog)!r}")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "catalog_id", catalog.id)
        object.__setattr__(self, f"_{type(self).__name__}__internal", catalog.internal)
        self.__internal.register_scope_var(dependency=self, default=default)

    def set(self, __value: T) -> ScopeVarToken[T]:
        old_value = self.__internal.update_scope_var(dependency=self, value=__value)
        return ScopeVarToken(
            cast(T, old_value) if old_value is not NotFoundSentinel else Missing.SENTINEL, var=self
        )

    def reset(self, __token: ScopeVarToken[T]) -> None:
        self.__internal.update_scope_var(
            dependency=self,
            value=__token.old_value
            if __token.old_value is not Missing.SENTINEL
            else NotFoundSentinel,
        )

    def __set_name__(self, owner: type, name: str) -> None:
        if "@" in self.name:
            object.__setattr__(self, "name", f"{debug_repr(owner)}.{name}")

    def __repr__(self) -> str:
        return f"ScopeVar(name={self.name}, catalog_id={self.catalog_id})"

    def __antidote_debug_repr__(self) -> str:
        return f"<scope-var> {self.name}"

    def __antidote_dependency_hint__(self) -> T:
        return cast(T, self)


@API.experimental
@final
@dataclass(frozen=True, eq=False)
class ScopeVarToken(Generic[T]):
    __slots__ = ("old_value", "var")
    old_value: T | Missing
    var: ScopeVar[T]
