import enum
import typing
from typing import Any, Callable, Type, TypeVar

from typing_extensions import Protocol, TypeGuard

from .debug import debug_repr, short_id
from .immutable import FinalImmutable, Immutable
from .meta import AbstractMeta, FinalMeta
from .. import API

Im = TypeVar('Im', bound=Immutable)
T = TypeVar('T')
Tp = TypeVar('Tp', bound=type)


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

# inspired by how `typing_extensions.runtime_checkable` checks for a protocol
# 3.8+
if hasattr(typing, 'runtime_checkable'):
    @API.private
    def _is_protocol(obj):
        return (issubclass(obj, typing.Generic)
                and getattr(obj, "_is_protocol", False))  # typing: ignore
else:
    ProtocolMeta = type(Protocol)


    @API.private
    def _is_protocol(obj):
        return isinstance(obj, ProtocolMeta) and getattr(obj, "_is_protocol", False)


@API.private
def _check(obj: Any, tpe: type, check: Callable[[Any, type], bool]) -> None:
    if _is_protocol(tpe):
        if getattr(tpe, "_is_runtime_protocol", False) and not check(obj, tpe):
            raise TypeError(f"{obj} is not an instance of {tpe}, but a {type(obj)}")
    elif not check(obj, tpe):
        raise TypeError(f"{obj!r} is not an instance of {tpe!r}, but a {type(obj)!r}")


@API.private
def enforce_type_if_possible(obj: object, tpe: Type[T]) -> TypeGuard[T]:
    return isinstance(tpe, type) and _check(obj, tpe, isinstance)


@API.private
def enforce_subclass_if_possible(child: type, mother: Tp) -> TypeGuard[Tp]:
    return (isinstance(mother, type)
            and isinstance(child, type)
            and _check(child, mother, issubclass))
