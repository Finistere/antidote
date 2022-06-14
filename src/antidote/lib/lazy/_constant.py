from __future__ import annotations

import functools
import inspect
import os
from dataclasses import dataclass
from typing import Any, Callable, cast, Generic, overload, Type, TypeVar

from typing_extensions import final, ParamSpec

from ..._internal import (
    API,
    auto_detect_var_name,
    debug_repr,
    Default,
    EMPTY_DICT,
    EMPTY_TUPLE,
    prepare_injection,
    retrieve_or_validate_injection_locals,
    Singleton,
    wraps_frozen,
)
from ..._internal.typing import Function
from ...core import (
    Catalog,
    CatalogId,
    Dependency,
    DependencyDebug,
    InjectedMethod,
    is_catalog,
    LifeTime,
    ProvidedDependency,
    ReadOnlyCatalog,
    TypeHintsLocals,
    world,
)
from ._provider import LazyDependency
from .constant import ConstantFactoryFunction, ConstFactory, ConstFactoryDecorator, is_const_factory

__all__ = ["ConstImpl", "ConstFactoryWrapper"]

P = ParamSpec("P")
T = TypeVar("T")


@API.private
@final
@dataclass(frozen=True, eq=False)
class ConstFactoryImpl(Singleton):
    __slots__ = ("method",)
    method: Any

    def __init__(self) -> None:
        object.__setattr__(self, "method", functools.partial(self.__call__, is_method=True))

    @overload
    def __call__(
        self,
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> ConstFactoryDecorator:
        ...

    @overload
    def __call__(
        self,
        __func: staticmethod[Callable[P, T]],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> staticmethod[ConstantFactoryFunction[P, T]]:
        ...

    @overload
    def __call__(
        self,
        __func: Callable[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> ConstantFactoryFunction[P, T]:
        ...

    def __call__(
        self,
        __func: object = None,
        *,
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
        is_method: bool = False,
    ) -> object:
        if not is_catalog(catalog):
            raise TypeError(f"catalog must be a Catalog, not a {type(catalog)!r}")

        inject_ = prepare_injection(
            inject=inject,
            catalog=catalog.private,
            type_hints_locals=retrieve_or_validate_injection_locals(type_hints_locals),
            method=is_method,
        )

        def decorate(func: Any) -> Any:
            if isinstance(func, staticmethod):
                if is_method:
                    raise TypeError("Use @const.factory for a staticmethod.")
                wrapped: Callable[..., object] = func.__func__
            elif isinstance(func, classmethod):
                raise TypeError("Cannot decorate a classmethod.")
            else:
                wrapped = func

            if is_const_factory(wrapped):
                raise TypeError(
                    f"Cannot apply @const.factory to an existing const factory function: {func}"
                )

            if not (callable(wrapped) and inspect.isfunction(wrapped)):
                raise TypeError("@const.factory can only be applied on a function.")

            # for PyRight because we use inspect.isfunction type guard.
            injected = inject_(cast(Callable[..., object], wrapped))

            if is_method:
                wrapper: Any = ConstantFactoryMethodImpl(
                    wrapped=wrapped,
                    injected_method=injected,  # type: ignore
                    catalog_id=catalog.id,
                )
            else:
                wrapper = ConstantFactoryFunctionImpl(
                    wrapped=wrapped,
                    injected=injected,
                    catalog_id=catalog.id,
                )

            if isinstance(func, staticmethod):
                return staticmethod(wrapper)
            return wrapper

        return __func and decorate(__func) or decorate


@API.private
@final
@dataclass(frozen=True, eq=False)
class ConstImpl(Singleton):
    factory: ConstFactory = ConstFactoryImpl()

    def __call__(self, __value: T, *, catalog: Catalog = world) -> Dependency[T]:
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
        cast: Type[T],
        catalog: Catalog = ...,
    ) -> Dependency[T]:
        ...

    @overload
    def env(
        self,
        __var_name: str = ...,
        *,
        default: T,
        cast: Type[T],
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
        cast: type | None = None,
        catalog: Catalog = world,
    ) -> object:
        if not isinstance(__var_name, (Default, str)):
            raise TypeError(f"Expected a string as first argument, not a {type(__var_name)!r}")

        if cast is not None and default is not Default.sentinel:
            if not isinstance(default, cast):
                raise TypeError(f"default value {default!r} does not match the cast type {cast!r}")

        return EnvConstantImpl[Any](
            var_name=__var_name,
            name=auto_detect_var_name(),
            catalog_id=catalog.id,
            default=default,
            cast=cast,
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
        self, catalog: ReadOnlyCatalog, out: ProvidedDependency
    ) -> None:
        out.set_value(value=self.value, lifetime=LifeTime.SINGLETON)

    def __antidote_dependency_hint__(self) -> T:
        return cast(T, self)


@API.private
@final
@dataclass(frozen=True, eq=False)
class EnvConstantImpl(Generic[T], LazyDependency):
    __slots__ = ("var_name", "catalog_id", "_inferred_name", "default", "cast")
    var_name: str | Default
    name: str
    catalog_id: CatalogId
    default: T | Default
    cast: Type[T] | None

    def __repr__(self) -> str:
        return (
            f"EnvConstant({self.name!r}, catalog_id={self.catalog_id}, var_name={self.var_name!r})"
        )

    def __antidote_debug__(self) -> DependencyDebug:
        return DependencyDebug(description=f"<const> {self.name}", lifetime=LifeTime.SINGLETON)

    def __antidote_unsafe_provide__(
        self, catalog: ReadOnlyCatalog, out: ProvidedDependency
    ) -> None:
        if isinstance(self.var_name, str):
            var_name: str = self.var_name
        elif "@" in self.name:
            var_name = self.name.rsplit("@", 1)[0]
        else:
            var_name = self.name.rsplit(".", 1)[1]
        try:
            value: object = os.environ[var_name]
        except LookupError:
            if isinstance(self.default, Default):
                raise
            value = self.default
        else:
            if self.cast is not None:
                value = self.cast(value)  # type: ignore

        out.set_value(value=value, lifetime=LifeTime.SINGLETON)

    def __antidote_dependency_hint__(self) -> T:
        return cast(T, self)

    def __set_name__(self, owner: type, name: str) -> None:
        object.__setattr__(self, "name", f"{debug_repr(owner)}.{name}")


@API.private
@final
@dataclass(frozen=True, eq=False)
class ConstantImpl(Generic[T], LazyDependency):
    __slots__ = ("name", "catalog_id", "__callback", "__args", "__kwargs")
    name: str
    catalog_id: CatalogId
    __callback: Function[..., T]
    __args: tuple[object, ...]
    __kwargs: dict[str, object]

    def __init__(
        self,
        *,
        catalog_id: CatalogId,
        callback: Callable[..., T],
        name: str,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> None:
        object.__setattr__(self, "catalog_id", catalog_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, f"_{type(self).__name__}__callback", callback)
        object.__setattr__(self, f"_{type(self).__name__}__args", args)
        object.__setattr__(self, f"_{type(self).__name__}__kwargs", kwargs)

    def __repr__(self) -> str:
        return (
            f"Constant({self.name!r}, catalog_id={self.catalog_id}, callback={self.__callback!r},"
            f"args={self.__args!r}, kwargs={self.__kwargs!r})"
        )

    def __set_name__(self, owner: type, name: str) -> None:
        object.__setattr__(self, "name", f"{debug_repr(owner)}.{name}")

    def __antidote_debug__(self) -> DependencyDebug:
        return DependencyDebug(
            description=f"<const> {self.name}", lifetime=LifeTime.SINGLETON, wired=self.__callback
        )

    def __antidote_unsafe_provide__(
        self, catalog: ReadOnlyCatalog, out: ProvidedDependency
    ) -> None:
        out.set_value(
            value=self.__callback(*self.__args, **self.__kwargs),
            lifetime=LifeTime.SINGLETON,
        )

    def __antidote_dependency_hint__(self) -> T:
        return cast(T, self)


@API.private
class ConstFactoryWrapper:
    __slots__ = ()


@API.private
@final
@dataclass(frozen=True, eq=False)
class ConstantFactoryFunctionImpl(ConstFactoryWrapper, Generic[P, T]):
    __slots__ = ("__injected", "__catalog_id", "__signature", "__dict__")
    __injected: Function[P, T]
    __signature: inspect.Signature
    __catalog_id: CatalogId

    def __init__(
        self, *, wrapped: Callable[..., object], injected: Callable[P, T], catalog_id: CatalogId
    ):
        object.__setattr__(self, f"_{type(self).__name__}__injected", injected)
        object.__setattr__(self, f"_{type(self).__name__}__signature", inspect.signature(wrapped))
        object.__setattr__(self, f"_{type(self).__name__}__catalog_id", catalog_id)
        wraps_frozen(wrapped, signature=self.__signature)(self)

    def __repr__(self) -> str:
        return f"ConstantFactoryFunction({self.__injected!r}, catalog_id={self.__catalog_id})"

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Dependency[T]:
        bound = self.__signature.bind(*args, **kwargs)
        return ConstantImpl[T](
            name=auto_detect_var_name(),
            callback=self.__injected,
            args=bound.args or EMPTY_TUPLE,
            kwargs=bound.kwargs or EMPTY_DICT,
            catalog_id=self.__catalog_id,
        )


@API.private
@final
@dataclass(frozen=True, eq=False)
class ConstantFactoryMethodImpl(ConstFactoryWrapper, Generic[P, T]):
    __slots__ = ("__injected_method", "__catalog_id", "__signature", "__owner", "__dict__")
    __injected_method: InjectedMethod[P, T]
    __signature: inspect.Signature
    __catalog_id: CatalogId
    __owner: type

    def __init__(
        self,
        *,
        wrapped: Callable[..., object],
        injected_method: InjectedMethod[P, T],
        catalog_id: CatalogId,
    ):
        signature: inspect.Signature = inspect.signature(wrapped)
        signature = signature.replace(parameters=list(signature.parameters.values())[1:])
        object.__setattr__(self, f"_{type(self).__name__}__injected_method", injected_method)
        object.__setattr__(self, f"_{type(self).__name__}__signature", signature)
        object.__setattr__(self, f"_{type(self).__name__}__catalog_id", catalog_id)
        wraps_frozen(wrapped, signature=self.__signature)(self)

    def __repr__(self) -> str:
        return f"ConstantFactoryMethod({self.__injected_method!r}, catalog_id={self.__catalog_id})"

    def __set_name__(self, owner: type, name: str) -> None:
        injected_method: InjectedMethod[[], T] = cast(Any, self.__injected_method)
        injected_method.__set_name__(owner, name)

    def __call__(self, *args: Any, **kwargs: Any) -> Dependency[T]:
        bound = self.__signature.bind(*args, **kwargs)
        return ConstantImpl(
            name=auto_detect_var_name(),
            callback=self.__injected_method,
            args=bound.args or EMPTY_TUPLE,
            kwargs=bound.kwargs or EMPTY_DICT,
            catalog_id=self.__catalog_id,
        )
