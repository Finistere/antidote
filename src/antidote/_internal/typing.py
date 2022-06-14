from __future__ import annotations

import sys
import typing
from typing import Any, Callable, cast, Optional, TypeVar, Union

from typing_extensions import get_args, get_origin, ParamSpec, Protocol, TypeGuard

__all__ = [
    "enforce_subclass_if_possible",
    "extract_optional_value",
    "is_optional",
    "optional_value",
    "Function",
]

T = TypeVar("T")
Tp = TypeVar("Tp", bound=type)
P = ParamSpec("P")
Out = TypeVar("Out", covariant=True)

if sys.version_info >= (3, 10):
    from types import UnionType
else:
    UnionType = Union

NoneType = type(None)

# inspired by how `typing_extensions.runtime_checkable` checks for a protocol
# 3.8+
if hasattr(typing, "runtime_checkable"):

    def _is_protocol(obj: type) -> bool:
        return issubclass(obj, typing.cast(type, typing.Generic)) and getattr(
            obj, "_is_protocol", False
        )

else:
    ProtocolMeta = type(Protocol)

    def _is_protocol(obj: type) -> bool:
        return isinstance(obj, ProtocolMeta) and getattr(obj, "_is_protocol", False)


def enforce_subclass_if_possible(child: type, mother: Tp) -> TypeGuard[Tp]:
    if isinstance(mother, type) and isinstance(child, type):
        _enforce(child, mother, issubclass)
    return True


def _enforce(obj: Any, tpe: type, check: Callable[[Any, type], bool]) -> None:
    if _is_protocol(tpe):
        if getattr(tpe, "_is_runtime_protocol", False) and not check(obj, tpe):
            raise TypeError(f"{obj} does not implement protocol {tpe}")
    elif not check(obj, tpe):
        raise TypeError(f"{obj!r} is not a {check.__name__} of {tpe!r}, but a {type(obj)!r}")


def extract_optional_value(type_hint: object) -> Optional[object]:
    while is_optional(type_hint):
        args = cast(Any, get_args(type_hint))
        return cast(object, args[0] if args[1] is NoneType else args[1])
    return None


def is_optional(type_hint: object) -> bool:
    args = cast(Any, get_args(type_hint))
    return _is_union(type_hint) and len(args) == 2 and (args[1] is NoneType or args[0] is NoneType)


def optional_value(optional: object) -> object:
    args = cast(Any, get_args(optional))
    return cast(object, args[0] if args[1] is NoneType else args[1])


def _is_union(type_hint: object) -> bool:
    origin = get_origin(type_hint)
    return origin is Union or origin is UnionType


# See https://github.com/python/mypy/issues/6910
class Function(Protocol[P, Out]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Out:
        ...


class Method(Protocol[P, Out]):
    def __call__(self, _: Any, *args: P.args, **kwargs: P.kwargs) -> Out:
        ...

    def __get__(self, instance: Any, owner: Any) -> Function[P, Out]:
        ...
