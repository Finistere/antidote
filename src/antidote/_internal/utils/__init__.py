import enum
import sys
import typing
from typing import Any, Callable, cast, Optional, Type, TypeVar, Union

from typing_extensions import get_args, get_origin, Protocol, TypeGuard

from .debug import debug_repr, short_id
from .immutable import FinalImmutable, Immutable
from .meta import AbstractMeta, FinalMeta
from .. import API

__all__ = [
    "debug_repr",
    "short_id",
    "FinalImmutable",
    "Immutable",
    "AbstractMeta",
    "FinalMeta",
    "API",
    "Default",
    "Copy",
    "enforce_subclass_if_possible",
    "enforce_type_if_possible",
    "extract_optional_value",
]

if sys.version_info >= (3, 10):
    from types import UnionType
else:
    UnionType = Union

Im = TypeVar("Im", bound=Immutable)
_T = TypeVar("_T")
_Tp = TypeVar("_Tp", bound=type)


@API.private
class Default(enum.Enum):
    sentinel = enum.auto()


@API.private
class Copy(enum.Enum):
    IDENTICAL = enum.auto()

    @staticmethod
    def immutable(current: Im, **kwargs: object) -> Im:
        return type(current)(
            **{
                attr: getattr(current, attr) if value is Copy.IDENTICAL else value
                for attr, value in kwargs.items()
            }
        )


# inspired by how `typing_extensions.runtime_checkable` checks for a protocol
# 3.8+
if hasattr(typing, "runtime_checkable"):

    @API.private
    def _is_protocol(obj: type) -> bool:
        return issubclass(obj, typing.cast(type, typing.Generic)) and getattr(
            obj, "_is_protocol", False
        )

else:
    ProtocolMeta = type(Protocol)

    @API.private
    def _is_protocol(obj: type) -> bool:
        return isinstance(obj, ProtocolMeta) and getattr(obj, "_is_protocol", False)


@API.private
def _enforce(obj: Any, tpe: type, check: Callable[[Any, type], bool]) -> None:
    if _is_protocol(tpe):
        if getattr(tpe, "_is_runtime_protocol", False) and not check(obj, tpe):
            raise TypeError(f"{obj} does not implement protocol {tpe}")
    elif not check(obj, tpe):
        raise TypeError(f"{obj!r} is not a {check.__name__} of {tpe!r}, but a {type(obj)!r}")


@API.private
def enforce_type_if_possible(obj: object, tpe: Type[_T]) -> TypeGuard[_T]:
    if isinstance(tpe, type):
        _enforce(obj, tpe, isinstance)
    return True


@API.private
def enforce_subclass_if_possible(child: type, mother: _Tp) -> TypeGuard[_Tp]:
    if isinstance(mother, type) and isinstance(child, type):
        _enforce(child, mother, issubclass)
    return True


@API.private
def is_union(type_hint: object) -> bool:
    origin = get_origin(type_hint)
    return origin is Union or origin is UnionType


@API.private
def is_optional(type_hint: object) -> bool:
    args = cast(Any, get_args(type_hint))
    return (
        is_union(type_hint)
        and len(args) == 2
        and (isinstance(None, args[1]) or isinstance(None, args[0]))
    )


@API.private
def extract_optional_value(type_hint: object) -> Optional[object]:
    if is_optional(type_hint):
        args = cast(Any, get_args(type_hint))
        return cast(object, args[0] if isinstance(None, args[1]) else args[1])
    return None
