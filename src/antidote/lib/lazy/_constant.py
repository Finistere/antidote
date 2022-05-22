from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, cast, Generic, Optional, Type, TypeVar, Union

from typing_extensions import final

from ._provider import Lazy
from .constant import (
    ConstantValueConverter,
    ConstantValueConverterMethod,
    ConstantValueProviderFunction,
    ConstantValueProviderMethod,
)
from ..._internal import API
from ..._internal.argspec import Arguments
from ..._internal.utils import debug_repr, Default, enforce_type_if_possible
from ...core import Container, Dependency, DependencyDebug, DependencyValue, Scope

__all__ = ["ConstantImpl"]

Arg = TypeVar("Arg", contravariant=True)
ProvidedValue = TypeVar("ProvidedValue")
Value = TypeVar("Value")


def get_singleton_instance(container: Container, cls: type) -> object:
    value = container.provide(cls)
    if value.scope is not Scope.singleton():
        raise RuntimeError(f"Expected const class {cls!r} to be a singleton.")
    return value.unwrapped


@API.private
class ConstantImpl(Generic[Arg, ProvidedValue, Value], Lazy, Dependency[Value]):
    __slots__ = ("name", "owner", "arg", "type_", "default", "provider", "provider", "converter")
    name: str
    owner: type
    arg: Optional[Arg]
    type_: Type[Value]
    default: Union[Value, Default]
    provider: object
    converter: object

    @classmethod
    def create(
        cls,
        *,
        arg: object,
        default: Union[Value, Default],
        type_: Type[Value],
        provider: (
            ConstantValueProviderFunction[Arg, ProvidedValue]
            | ConstantValueProviderMethod[Arg, ProvidedValue]
        ),
        converter: Optional[
            ConstantValueConverter[ProvidedValue] | ConstantValueConverterMethod[ProvidedValue]
        ],
    ) -> ConstantImpl[Arg, ProvidedValue, Value]:
        if Arguments.from_callable(provider, ignore_type_hints=True).has_self:
            if (
                converter is not None
                and not Arguments.from_callable(converter, ignore_type_hints=True).has_self
            ):

                def wrapped_converter(self: Any, value: Any, tpe: Any) -> Any:
                    return cast(ConstantValueConverter[ProvidedValue], converter)(
                        value=value, tpe=tpe
                    )

                return ConstantMethImpl(
                    arg=arg,
                    default=default,
                    type_=type_,
                    provider=provider,
                    converter=wrapped_converter,
                )
            return ConstantMethImpl(
                arg=arg, default=default, type_=type_, provider=provider, converter=converter
            )
        return ConstantFuncImpl(
            arg=arg, default=default, type_=type_, provider=provider, converter=converter
        )

    def __init__(
        self,
        *,
        arg: object,
        default: Union[Value, Default],
        type_: Type[Value],
        provider: object,
        converter: object,
    ) -> None:
        object.__setattr__(self, "arg", arg)
        object.__setattr__(self, "type_", type_)
        object.__setattr__(self, "default", default)
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "converter", converter)

    def __set_name__(self, owner: type, name: str) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "owner", owner)

    def __repr__(self) -> str:
        try:
            _: object = self.name
            _ = self.owner
        except AttributeError:
            return (
                f"ConstantImpl("
                f"arg={self.arg!r}, "
                f"default={self.default!r}, "
                f"type={self.type_!r}, "
                f"provider={self.provider!r}, "
                f"converter={self.converter!r}"
                f")"
            )
        return (
            f"ConstantImpl("
            f"arg={self.arg!r}, "
            f"default={self.default!r}, "
            f"type={self.type_!r}, "
            f"provider={self.provider!r}, "
            f"converter={self.converter!r}, "
            f"name={self.name!r}, "
            f"owner={self.owner!r}"
            f")"
        )

    def __get__(self, instance: Optional[object], owner: type) -> Value:
        if instance is None:
            return cast(Value, self)
        return self._provide(lambda: instance)

    def __antidote_provide__(self, container: Container) -> DependencyValue:
        return DependencyValue(
            self._provide(lambda: get_singleton_instance(container, self.owner)),
            scope=Scope.singleton(),
        )

    def _provide(self, get_provider_self: Callable[[], object]) -> Value:
        raise NotImplementedError()  # pragma: no cover


@API.private
@final
@dataclass(frozen=True, init=False, eq=False, unsafe_hash=False, repr=False)
class ConstantFuncImpl(ConstantImpl[Arg, ProvidedValue, Value]):
    provider: ConstantValueProviderFunction[Arg, ProvidedValue]
    converter: Optional[ConstantValueConverter[ProvidedValue]]

    def __antidote_debug_info__(self) -> DependencyDebug:
        return DependencyDebug(
            f"{debug_repr(self.owner)}.{self.name}",
            scope=Scope.singleton(),
            wired=[self.provider, self.converter],
        )

    def _provide(self, get_provider_self: Callable[[], object]) -> Value:
        value: ProvidedValue
        try:
            value = self.provider(name=self.name, arg=self.arg)
        except LookupError:
            if self.default is Default.sentinel:
                raise
            result: Value = self.default
        else:
            if self.converter is not None:
                result = self.converter(value=value, tpe=self.type_)
            else:
                result = cast(Value, value)

        assert enforce_type_if_possible(result, self.type_)
        return cast(Value, result)  # for Mypy, typeguard not working properly


@API.private
@final
@dataclass(frozen=True, init=False, eq=False, unsafe_hash=False, repr=False)
class ConstantMethImpl(ConstantImpl[Arg, ProvidedValue, Value]):
    provider: ConstantValueProviderMethod[Arg, ProvidedValue]
    converter: Optional[ConstantValueConverterMethod[ProvidedValue]]

    def __antidote_debug_info__(self) -> DependencyDebug:
        return DependencyDebug(
            f"{debug_repr(self.owner)}.{self.name}",
            scope=Scope.singleton(),
            wired=[self.provider, self.converter, self.owner],
        )

    def _provide(self, get_provider_self: Callable[[], object]) -> Value:
        provider_self = get_provider_self()
        value: ProvidedValue
        try:
            value = self.provider(provider_self, name=self.name, arg=self.arg)
        except LookupError:
            if self.default is Default.sentinel:
                raise
            result: Value = self.default
        else:
            if self.converter is not None:
                result = self.converter(provider_self, value=value, tpe=self.type_)
            else:
                result = cast(Value, value)

        assert enforce_type_if_possible(result, self.type_)
        return cast(Value, result)  # for Mypy, typeguard not working properly
