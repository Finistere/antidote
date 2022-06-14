from __future__ import annotations

import enum
import inspect
from dataclasses import dataclass
from typing import Any, Callable, cast, Generic, overload, TypeVar

from typing_extensions import final, ParamSpec

from ..._internal import (
    API,
    debug_repr,
    Default,
    EMPTY_DICT,
    EMPTY_TUPLE,
    prepare_injection,
    retrieve_or_validate_injection_locals,
    short_id,
    Singleton,
    wraps_frozen,
)
from ...core import (
    CatalogId,
    DuplicateDependencyError,
    InjectedMethod,
    is_catalog,
    LifetimeType,
    TypeHintsLocals,
    world,
)
from ._provider import lazy_call
from .lazy import DecoratorLazyFunction, is_lazy, LazyFunction

__all__ = [
    "LazyImpl",
    "LazyWrapper",
]

from ..._internal.typing import Function
from ...core import Catalog, Dependency, LifeTime

T = TypeVar("T")
P = ParamSpec("P")
Out = TypeVar("Out", covariant=True)


@API.private
@final
class FunctionKind(enum.Enum):
    FUNCTION = 1
    METHOD = 2
    PROPERTY = 3
    VALUE = 4


@API.private
@final
@dataclass(frozen=True, eq=False)
class LazyImpl(Singleton):
    __slots__ = ("method", "property", "value")
    method: Any
    property: Any
    value: Any

    def __init__(self) -> None:
        def method(*args: Any, **kwargs: Any) -> Any:
            kwargs["_kind"] = FunctionKind.METHOD
            kwargs["type_hints_locals"] = retrieve_or_validate_injection_locals(
                kwargs.get("type_hints_locals", Default.sentinel)
            )
            return self(*args, **kwargs)

        def property(*args: Any, **kwargs: Any) -> Any:
            kwargs["_kind"] = FunctionKind.PROPERTY
            kwargs["type_hints_locals"] = retrieve_or_validate_injection_locals(
                kwargs.get("type_hints_locals", Default.sentinel)
            )
            return self(*args, **kwargs)

        def value(*args: Any, **kwargs: Any) -> Any:
            kwargs["_kind"] = FunctionKind.VALUE
            kwargs["type_hints_locals"] = retrieve_or_validate_injection_locals(
                kwargs.get("type_hints_locals", Default.sentinel)
            )
            return self(*args, **kwargs)

        object.__setattr__(self, "method", method)
        object.__setattr__(self, "property", property)
        object.__setattr__(self, "value", value)

    @overload
    def __call__(
        self,
        *,
        lifetime: LifetimeType = ...,
        inject: None | Default = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> DecoratorLazyFunction:
        ...

    @overload
    def __call__(
        self,
        __func: staticmethod[Callable[P, T]],
        *,
        lifetime: LifetimeType = ...,
        inject: None | Default = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> staticmethod[LazyFunction[P, T]]:
        ...

    @overload
    def __call__(
        self,
        __func: Callable[P, T],
        *,
        lifetime: LifetimeType = ...,
        inject: None | Default = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> LazyFunction[P, T]:
        ...

    def __call__(
        self,
        __func: object = None,
        *,
        lifetime: LifetimeType = "transient",
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
        _kind: FunctionKind = FunctionKind.FUNCTION,
    ) -> object:
        if not is_catalog(catalog):
            raise TypeError(f"catalog must be a Catalog, not a {type(catalog)!r}")

        inject_ = prepare_injection(
            inject=inject,
            catalog=catalog.private,
            type_hints_locals=retrieve_or_validate_injection_locals(type_hints_locals),
            method=_kind in {FunctionKind.METHOD, FunctionKind.PROPERTY},
        )

        def decorate(func: Any, lifetime: LifeTime = LifeTime.of(lifetime)) -> Any:
            if isinstance(func, staticmethod):
                if _kind is not FunctionKind.FUNCTION:
                    raise TypeError("Use @lazy for a staticmethod.")
                wrapped: Callable[..., object] = func.__func__
            elif isinstance(func, classmethod):
                raise TypeError("Cannot decorate a classmethod.")
            else:
                wrapped = func

            if is_lazy(wrapped):
                raise DuplicateDependencyError(
                    f"Cannot apply @lazy to an existing lazy function: {func}"
                )

            if not (callable(wrapped) and inspect.isfunction(wrapped)):
                raise TypeError("lazy can only be applied on a function.")

            # for PyRight because we use inspect.isfunction type guard.
            injected = inject_(cast(Callable[..., object], wrapped))

            if _kind is FunctionKind.METHOD:
                wrapper: Any = LazyMethodImpl(
                    wrapped=wrapped,
                    injected_method=injected,  # type: ignore
                    lifetime=lifetime,
                    catalog_id=catalog.id,
                )
            elif _kind is FunctionKind.PROPERTY:
                return LazyPropertyImpl(
                    wrapped=wrapped,
                    injected_method=injected,  # type: ignore
                    lifetime=lifetime,
                    catalog_id=catalog.id,
                )
            elif _kind is FunctionKind.FUNCTION:
                wrapper = LazyFunctionImpl(
                    wrapped=wrapped,
                    injected=injected,
                    lifetime=lifetime,
                    catalog_id=catalog.id,
                )
            else:
                assert _kind is FunctionKind.VALUE
                return LazyValue(
                    wrapped=wrapped,
                    injected=injected,
                    lifetime=lifetime,
                    catalog_id=catalog.id,
                )

            if isinstance(func, staticmethod):
                return staticmethod(wrapper)
            return wrapper

        return __func and decorate(__func) or decorate


@API.private
class LazyWrapper:
    __slots__ = ()


@API.private
@final
@dataclass(frozen=True, eq=False)
class LazyValue(LazyWrapper, Generic[Out]):
    __slots__ = ("__dependency", "__injected", "__catalog_id", "__dict__")
    __dependency: Dependency[Out]
    __injected: Function[[], Out]
    __catalog_id: CatalogId

    def __init__(
        self,
        *,
        wrapped: Callable[..., object],
        injected: Callable[[], Out],
        catalog_id: CatalogId,
        lifetime: LifeTime,
    ) -> None:
        object.__setattr__(self, f"_{type(self).__name__}__injected", injected)
        object.__setattr__(self, f"_{type(self).__name__}__catalog_id", catalog_id)
        object.__setattr__(
            self,
            f"_{type(self).__name__}__dependency",
            lazy_call(
                func=injected,
                args=EMPTY_TUPLE,
                kwargs=EMPTY_DICT,
                lifetime=lifetime,
                catalog_id=catalog_id,
            ),
        )
        wraps_frozen(wrapped)(self)

    def __antidote_debug_repr__(self) -> str:
        return f"<lazy value {debug_repr(self.__injected)} #{short_id(self)}>"

    def __antidote_dependency_hint__(self) -> Out:
        return cast(Out, self.__dependency)

    def __repr__(self) -> str:
        return f"LazyValue({self.__injected}, catalog_id={self.__catalog_id})"


@API.private
@final
@dataclass(frozen=True, eq=False)
class LazyPropertyImpl(LazyWrapper, Generic[P, Out]):
    __slots__ = (
        "__catalog_id",
        "__lifetime",
        "__injected_method",
        "__auto_self_dependency",
        "__dict__",
    )
    __catalog_id: CatalogId
    __lifetime: LifeTime
    __injected_method: InjectedMethod[[], Out]
    __auto_self_dependency: Dependency[Out]

    def __init__(
        self,
        *,
        wrapped: Callable[..., object],
        injected_method: InjectedMethod[[], Out],
        lifetime: LifeTime,
        catalog_id: CatalogId,
    ) -> None:
        object.__setattr__(self, f"_{type(self).__name__}__lifetime", lifetime)
        object.__setattr__(self, f"_{type(self).__name__}__injected_method", injected_method)
        object.__setattr__(self, f"_{type(self).__name__}__catalog_id", catalog_id)
        wraps_frozen(wrapped)(self)

    def __set_name__(self, owner: type, name: str) -> None:
        injected_method: InjectedMethod[[], Out] = cast(Any, self.__injected_method)
        injected_method.__set_name__(owner, name)

        object.__setattr__(
            self,
            f"_{type(self).__name__}__auto_self_dependency",
            lazy_call(
                func=injected_method,
                args=EMPTY_TUPLE,
                kwargs=EMPTY_DICT,
                lifetime=self.__lifetime,
                catalog_id=self.__catalog_id,
            ),
        )

    def __antidote_debug_repr__(self) -> str:
        return f"<lazy property {debug_repr(self.__injected_method)} #{short_id(self)}>"

    def __antidote_dependency_hint__(self) -> Out:
        return cast(Out, self.__auto_self_dependency)

    def __repr__(self) -> str:
        return f"TransientLazyProperty(wrapped={self.__injected_method}, catalog_id={self.__catalog_id})"


@API.private
@final
@dataclass(frozen=True, eq=False)
class LazyMethodImpl(LazyWrapper, Generic[P, Out]):
    __slots__ = (
        "__catalog_id",
        "__injected_method",
        "__cache",
        "__lifetime",
        "__signature",
        "__lazy_auto_self",
        "__dict__",
    )
    __signature: inspect.Signature
    __injected_method: InjectedMethod[P, Out]
    __lifetime: LifeTime
    __catalog_id: CatalogId

    def __init__(
        self,
        *,
        wrapped: Callable[..., object],
        injected_method: InjectedMethod[P, Out],
        lifetime: LifeTime,
        catalog_id: CatalogId,
    ) -> None:
        signature: inspect.Signature = inspect.signature(wrapped)
        signature = signature.replace(parameters=list(signature.parameters.values())[1:])
        object.__setattr__(self, f"_{type(self).__name__}__signature", signature)
        object.__setattr__(self, f"_{type(self).__name__}__injected_method", injected_method)
        object.__setattr__(self, f"_{type(self).__name__}__lifetime", lifetime)
        object.__setattr__(self, f"_{type(self).__name__}__catalog_id", catalog_id)
        wraps_frozen(wrapped, signature=signature)(self)

    def __set_name__(self, owner: type, name: str) -> None:
        injected_method: InjectedMethod[[], Out] = cast(Any, self.__injected_method)
        injected_method.__set_name__(owner, name)

    def __antidote_debug_repr__(self) -> str:
        return f"<lazy method {debug_repr(self.__injected_method)} #{short_id(self)}>"

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Dependency[Out]:
        bound = self.__signature.bind(*args, **kwargs)
        return lazy_call(
            func=self.__injected_method,
            args=bound.args or EMPTY_TUPLE,
            kwargs=bound.kwargs or EMPTY_DICT,
            lifetime=self.__lifetime,
            catalog_id=self.__catalog_id,
        )

    def __repr__(self) -> str:
        return f"LazyMethod(wrapped={self.__injected_method}, catalog_id={self.__catalog_id})"


@API.private
@final
@dataclass(frozen=True, eq=False)
class LazyFunctionImpl(LazyWrapper, Generic[P, Out]):
    __slots__ = (
        "__catalog_id",
        "__injected",
        "__dependency_cache",
        "__lifetime",
        "__signature",
        "__dict__",
    )
    __signature: inspect.Signature
    __lifetime: LifeTime
    __catalog_id: CatalogId
    __injected: Function[P, Out]

    def __init__(
        self,
        *,
        wrapped: Callable[..., object],
        injected: Callable[P, Out],
        lifetime: LifeTime,
        catalog_id: CatalogId,
    ) -> None:
        object.__setattr__(self, f"_{type(self).__name__}__signature", inspect.signature(wrapped))
        object.__setattr__(self, f"_{type(self).__name__}__injected", injected)
        object.__setattr__(self, f"_{type(self).__name__}__lifetime", lifetime)
        object.__setattr__(self, f"_{type(self).__name__}__catalog_id", catalog_id)
        wraps_frozen(wrapped, signature=self.__signature)(self)

    def __antidote_debug_repr__(self) -> str:
        return f"<lazy function {debug_repr(self.__injected)} #{short_id(self)}>"

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Dependency[Out]:
        bound = self.__signature.bind(*args, **kwargs)
        return lazy_call(
            func=self.__injected,
            args=bound.args or EMPTY_TUPLE,
            kwargs=bound.kwargs or EMPTY_DICT,
            lifetime=self.__lifetime,
            catalog_id=self.__catalog_id,
        )

    def __repr__(self) -> str:
        return f"LazyFunction(wrapped={self.__injected}, catalog_id={self.__catalog_id})"
