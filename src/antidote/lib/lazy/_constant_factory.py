from __future__ import annotations

import dataclasses
import functools
import inspect
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast, Generic, Optional, Type, TypeVar, Union

from typing_extensions import final, get_type_hints

from ._constant import ConstantImpl
from .constant import (
    Constant,
    ConstantFactory,
    ConstantValueConverter,
    ConstantValueConverterMethod,
    ConstantValueProvider,
    ConstantValueProviderFunction,
    ConstantValueProviderMethod,
    TypedConstantFactory,
)
from ..._internal import API
from ..._internal.utils import Default, enforce_type_if_possible
from ..._internal.utils.meta import Singleton
from ...core import inject
from ...core.exceptions import DoubleInjectionError

T = TypeVar("T")
Arg = TypeVar("Arg", contravariant=True)
Value = TypeVar("Value")
ProvidedValue = TypeVar("ProvidedValue")
ValueCo = TypeVar("ValueCo", covariant=True)


@API.private
def const_env_provider(name: str, arg: Optional[str]) -> str:
    return os.environ[arg or name]


@API.private
def const_env_converter(value: str, tpe: Type[T]) -> T:
    if issubclass(tpe, (str, int, float, Enum)):
        return cast(T, tpe(value))  # for MyPy
    raise TypeError(f"Unsupported type {tpe!r}")


@API.private
def const_identity_provider(name: str, arg: object) -> object:
    assert arg is not None
    return arg


@API.private
@final
@dataclass(frozen=True, eq=False)
class ConstantFactoryImpl(Generic[Arg, Value]):
    """ """

    __slots__ = ("provider", "converter", "inferred_type_")
    provider: ConstantValueProviderFunction[Arg, Value] | ConstantValueProviderMethod[Arg, Value]
    converter: Optional[ConstantValueConverter[Value] | ConstantValueConverterMethod[Value]]
    inferred_type_: Optional[Type[Value]]

    @classmethod
    def create(
        cls,
        provider: (
            ConstantValueProviderFunction[Arg, Value] | ConstantValueProviderMethod[Arg, Value]
        ),
        converter: Optional[ConstantValueConverter[Value]] = None,
    ) -> ConstantFactoryImpl[Arg, Value]:
        type_hint = get_type_hints(provider).get("return")
        return ConstantFactoryImpl[Arg, Value](
            provider=provider,
            converter=converter,
            inferred_type_=cast(Type[Value], type_hint) if isinstance(type_hint, type) else None,
        )

    def with_converter(
        self, __func: ConstantValueConverter[Value] | ConstantValueConverterMethod[Value]
    ) -> ConstantFactoryImpl[Arg, Value]:
        if not inspect.isfunction(__func):
            raise TypeError(f"Expected as function for the converter, not a {type(__func)!r}")
        signature = inspect.signature(__func)
        if "value" not in signature.parameters or "tpe" not in signature.parameters:
            raise TypeError(f"Either 'value' or 'tpe' argument was not found in {__func!r}")

        return dataclasses.replace(self, converter=__func)

    def __call__(
        self,
        __arg: Optional[Arg] = None,
        *,
        default: Union[Value, Default] = Default.sentinel,
    ) -> Constant[Value]:
        type_ = (
            self.inferred_type_ if self.inferred_type_ is not None else cast(Type[Value], object)
        )
        if default is not Default.sentinel:
            enforce_type_if_possible(default, type_)
        return ConstantImpl.create(
            arg=__arg, default=default, type_=type_, provider=self.provider, converter=None
        )

    def __getitem__(self, __type: Type[T]) -> TypedConstantFactory[Arg, T]:
        return TypedConstantFactoryImpl[Arg, Value, T](
            provider=self.provider, converter=self.converter, type_=__type
        )


@API.private
@final
@dataclass(frozen=True, eq=False)
class TypedConstantFactoryImpl(Generic[Arg, ProvidedValue, Value]):
    __slots__ = ("provider", "converter", "type_")
    provider: (
        ConstantValueProviderFunction[Arg, ProvidedValue]
        | ConstantValueProviderMethod[Arg, ProvidedValue]
    )
    converter: Optional[
        ConstantValueConverter[ProvidedValue] | ConstantValueConverterMethod[ProvidedValue]
    ]
    type_: Type[Value]

    def __call__(
        self, __arg: object = None, *, default: Union[Value, Default] = Default.sentinel
    ) -> Constant[Value]:
        if default is not Default.sentinel:
            enforce_type_if_possible(default, self.type_)
        return ConstantImpl.create(
            arg=__arg,
            default=default,
            type_=self.type_,
            provider=self.provider,
            converter=self.converter,
        )


@API.private
@final
@dataclass
class ConstantProviderImpl(Generic[Arg, Value]):
    __wrapped__: ConstantValueProviderFunction[Arg, Value] | ConstantValueProviderMethod[Arg, Value]
    const: ConstantFactoryImpl[Arg, Value]

    def __post_init__(self) -> None:
        functools.wraps(self.__wrapped__)(self)

    def __get__(self, instance: object, owner: type) -> ConstantValueProviderFunction[Arg, Value]:
        return cast(
            ConstantValueProviderFunction[Arg, Value],
            self.__wrapped__.__get__(instance, owner),  # type: ignore
        )

    def __call__(self, *args: Any, **kwargs: Any) -> Value:
        return self.__wrapped__(*args, **kwargs)  # supporting both method and function.

    def converter(
        self, __func: ConstantValueConverter[Value] | ConstantValueConverterMethod[Value]
    ) -> ConstantValueConverter[Value]:
        if self.const.converter is not None:
            raise RuntimeError(f"Converter was already defined as {self.const.converter!r}")
        self.const = self.const.with_converter(__func)
        return cast(ConstantValueConverter[Value], __func)


@API.private
@final
@dataclass(frozen=True, eq=False)
class ConstImpl(Singleton):
    __slots__ = ("identity", "env")
    identity: ConstantFactory[object, object]
    env: ConstantFactory[str, str]

    def __init__(self) -> None:
        object.__setattr__(
            self, "identity", ConstantFactoryImpl.create(provider=const_identity_provider)
        )
        object.__setattr__(
            self,
            "env",
            ConstantFactoryImpl.create(provider=const_env_provider, converter=const_env_converter),
        )

    def __call__(
        self,
        __value: Optional[Value] = None,
        *,
        default: Union[Value, Default] = Default.sentinel,
    ) -> Constant[Value]:
        return cast(Constant[Value], self.identity(__value, default=default))

    def __getitem__(self, __type: Type[T]) -> TypedConstantFactory[object, T]:
        return self.identity[__type]

    def provider(
        self, __func: ConstantValueProviderFunction[Arg, T] | ConstantValueProviderMethod[Arg, T]
    ) -> ConstantValueProvider[Arg, T]:
        if not inspect.isfunction(__func):
            raise TypeError("@const.provider can only be applied on a function or a method.")
        signature = inspect.signature(__func)
        if "name" not in signature.parameters or "arg" not in signature.parameters:
            raise TypeError(f"Either 'name' or 'arg' argument was not found in {__func!r}")

        try:
            __func = inject(__func)
        except DoubleInjectionError:
            pass

        return ConstantProviderImpl[Arg, T](
            __func, const=ConstantFactoryImpl.create(provider=__func)
        )
