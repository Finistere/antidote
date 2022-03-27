import enum
import typing

from typing import TypeVar, Type
from typing_extensions import Protocol, TypeGuard

from .debug import debug_repr, short_id
from .immutable import FinalImmutable, Immutable
from .meta import AbstractMeta, FinalMeta
from .. import API

Im = typing.TypeVar('Im', bound=Immutable)
T = TypeVar('T')

@API.private
class Default(enum.Enum):
    sentinel = enum.auto()


@API.private
class Copy(enum.Enum):
    IDENTICAL = enum.auto()

    @staticmethod
    def immutable(current: Im, **kwargs: object) -> Im:
        return type(current)(**{
            attr: getattr(current, attr) if value is Copy.IDENTICAL else value
            for attr, value in kwargs.items()
        })


__all__ = ['debug_repr', 'short_id', 'FinalImmutable', 'Immutable', 'AbstractMeta',
           'FinalMeta', 'API', 'Default', 'Copy']

# 3.8+
if hasattr(typing, 'runtime_checkable'):

    @API.private
    def enforce_type_if_possible(obj: object, tpe: Type[T]) -> TypeGuard[T]:
        if not isinstance(tpe, type):
            return

        # inspired by how `typing.runtime_checkable` checks for a protocol
        if issubclass(tpe, typing.Generic) and getattr(tpe, "_is_protocol", False):  # type: ignore
            if getattr(tpe, "_is_runtime_protocol", False) and not isinstance(obj, tpe):
                raise TypeError(f"Dependency value {obj} is not an instance of {tpe}, "
                                f"but a {type(obj)}")
        elif not isinstance(obj, tpe):
            raise TypeError(f"Dependency value {obj} is not an instance of {tpe}, "
                            f"but a {type(obj)}")
else:
    ProtocolMeta = type(Protocol)

    @API.private
    def enforce_type_if_possible(obj: object, tpe: Type[T]) -> TypeGuard[T]:
        if not isinstance(tpe, type):
            return

        # inspired by how `typing_extensions.runtime_checkable` checks for a protocol
        if isinstance(tpe, ProtocolMeta) and getattr(tpe, "_is_protocol", False):
            if getattr(tpe, "_is_runtime_protocol", False) and not isinstance(obj, tpe):
                raise TypeError(f"Dependency value {obj} is not an instance of {tpe}, "
                                f"but a {type(obj)}")
        elif not isinstance(obj, tpe):
            raise TypeError(f"Value {obj!r} is not an instance of {tpe!r}, "
                            f"but a {type(obj)!r}")
