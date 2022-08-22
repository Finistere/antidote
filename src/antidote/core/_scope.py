from __future__ import annotations

from abc import ABC
from typing import Any, cast, Generic, TYPE_CHECKING, TypeVar

from .._internal import API, debug_repr, Default
from ._catalog import CatalogImpl, CatalogOnion
from ._raw import NotFoundSentinel
from .data import CatalogId

if TYPE_CHECKING:
    from . import Catalog, ScopeVarToken

__all__ = ["AbstractScopeVar"]

T = TypeVar("T")


@API.private
class AbstractScopeVar(Generic[T], ABC):
    __slots__ = ("name", "catalog_id", "__onion")
    name: str
    catalog_id: CatalogId
    __onion: CatalogOnion

    def __init__(
        self,
        *,
        name: str,
        default: T | Default = Default.sentinel,
        catalog: Catalog | Default = Default.sentinel,
    ) -> None:
        from ._objects import world

        if isinstance(catalog, Default):
            catalog = world

        if not isinstance(catalog, CatalogImpl):
            raise TypeError(f"catalog must be a Catalog, not a {type(catalog)!r}")
        catalog.raise_if_frozen()

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "catalog_id", catalog.id)
        object.__setattr__(self, f"_{AbstractScopeVar.__name__}__onion", catalog.onion)
        self.__onion.layer.register_scope_var(dependency=self, default=default)

    def set(self, __value: T) -> ScopeVarToken[T, Any]:
        from .scope import Missing, ScopeVarToken

        old_value = self.__onion.layer.update_scope_var(dependency=self, value=__value)
        return ScopeVarToken(
            cast(T, old_value) if old_value is not NotFoundSentinel else Missing.SENTINEL, var=self
        )

    def reset(self, __token: ScopeVarToken[T, Any]) -> None:
        from .scope import Missing

        self.__onion.layer.update_scope_var(
            dependency=self,
            value=__token.old_value
            if __token.old_value is not Missing.SENTINEL
            else NotFoundSentinel,
        )

    def __set_name__(self, owner: type, name: str) -> None:
        if "@" in self.name:
            object.__setattr__(self, "name", f"{debug_repr(owner)}.{name}")

    def __antidote_dependency_hint__(self) -> T:
        return cast(T, self)
