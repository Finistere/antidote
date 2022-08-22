from __future__ import annotations

import inspect
import os
from dataclasses import dataclass
from typing import Any, Callable, cast, Generic, overload, Type

from typing_extensions import final

from ..._internal import API, auto_detect_var_name, debug_repr, Default, Singleton
from ..._internal.typing import Function, T
from ...core import (
    Catalog,
    CatalogId,
    Dependency,
    DependencyDebug,
    LifeTime,
    ProvidedDependency,
    ProviderCatalog,
    world,
)
from ._provider import LazyDependency

__all__ = ["ConstImpl"]


@API.private
@final
@dataclass(frozen=True, eq=False)
class ConstImpl(Singleton):
    def __call__(self, __value: T, *, catalog: Catalog = world) -> Dependency[T]:
        catalog.raise_if_frozen()
        return StaticConstantImpl[T](value=__value, catalog_id=catalog.id)

    @overload
    def env(
        self,
        __var_name: str = ...,
        *,
        catalog: Catalog = ...,
    ) -> Dependency[str]:
        ...

    @overload
    def env(
        self,
        __var_name: str = ...,
        *,
        convert: Type[T] | Callable[[str], T],
        catalog: Catalog = ...,
    ) -> Dependency[T]:
        ...

    @overload
    def env(
        self,
        __var_name: str = ...,
        *,
        default: T,
        convert: Type[T] | Callable[[str], T],
        catalog: Catalog = ...,
    ) -> Dependency[T]:
        ...

    @overload
    def env(
        self,
        __var_name: str = ...,
        *,
        default: T,
        catalog: Catalog = ...,
    ) -> Dependency[T]:
        ...

    def env(
        self,
        __var_name: str | Default = Default.sentinel,
        *,
        default: object = Default.sentinel,
        convert: object | None = None,
        catalog: Catalog = world,
    ) -> object:
        catalog.raise_if_frozen()
        if not isinstance(__var_name, (Default, str)):
            raise TypeError(f"Expected a string as first argument, not a {type(__var_name)!r}")

        if not (convert is None or isinstance(convert, type) or inspect.isfunction(convert)):
            raise TypeError(f"convert must be a type, a function or None, not a {type(convert)!r}")

        if isinstance(convert, type) and default is not Default.sentinel:
            if not isinstance(default, convert):
                raise TypeError(
                    f"default value {default!r} does not match " f"the convert type {convert!r}"
                )

        return EnvConstantImpl[Any](
            var_name=__var_name,
            name=auto_detect_var_name(),
            catalog_id=catalog.id,
            default=default,
            convert=cast(Callable[[str], Any], convert),
        )


@API.private
@final
@dataclass(frozen=True, eq=False)
class StaticConstantImpl(Generic[T], LazyDependency):
    __slots__ = ("catalog_id", "value")
    catalog_id: CatalogId
    value: T

    def __repr__(self) -> str:
        return f"StaticConstant({self.value!r}, catalog_id={self.catalog_id})"

    def __antidote_debug__(self) -> DependencyDebug:
        return DependencyDebug(
            description=f"<const> {debug_repr(self.value)}", lifetime=LifeTime.SINGLETON
        )

    def __antidote_unsafe_provide__(
        self, catalog: ProviderCatalog, out: ProvidedDependency
    ) -> None:
        out.set_value(value=self.value, lifetime=LifeTime.SINGLETON)

    def __antidote_dependency_hint__(self) -> T:
        return cast(T, self)


@API.private
@final
@dataclass(frozen=True, eq=False)
class EnvConstantImpl(Generic[T], LazyDependency):
    __slots__ = ("var_name", "catalog_id", "_inferred_name", "default", "convert")
    var_name: str | Default
    name: str
    catalog_id: CatalogId
    default: T | Default
    convert: Function[[str], T]

    def __repr__(self) -> str:
        return (
            f"EnvConstant({self.name!r}, catalog_id={self.catalog_id}, var_name={self.var_name!r})"
        )

    def __antidote_debug__(self) -> DependencyDebug:
        return DependencyDebug(description=f"<const> {self.name}", lifetime=LifeTime.SINGLETON)

    def __antidote_unsafe_provide__(
        self, catalog: ProviderCatalog, out: ProvidedDependency
    ) -> None:
        if isinstance(self.var_name, str):
            var_name: str = self.var_name
        elif "@" in self.name:
            var_name = self.name.rsplit("@", 1)[0]
        else:
            var_name = self.name.rsplit(".", 1)[1]
        try:
            value: Any = os.environ[var_name]
        except LookupError:
            if isinstance(self.default, Default):
                raise
            value = self.default
        else:
            if self.convert is not None:
                value = self.convert(value)

        out.set_value(value=value, lifetime=LifeTime.SINGLETON)

    def __antidote_dependency_hint__(self) -> T:
        return cast(T, self)

    def __set_name__(self, owner: type, name: str) -> None:
        object.__setattr__(self, "name", f"{debug_repr(owner)}.{name}")
