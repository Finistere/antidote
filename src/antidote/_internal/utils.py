from __future__ import annotations

import base64
import dis
import enum
import functools
import inspect
import re
import types
import weakref
from typing import Any, Callable, ClassVar, Mapping, Optional, TYPE_CHECKING, TypeVar

from typing_extensions import final

if TYPE_CHECKING:
    from ..core import Catalog

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

# Object will be allocated on the heap, so as close as possible to most user objects
# in memory.
_ID_MASK = id(object())


def short_id(__obj: object) -> str:
    """Produces a short, human-readable, representation of the id of an object."""
    n = id(__obj) ^ _ID_MASK
    return (
        base64.b64encode(n.to_bytes(8, byteorder="little"))
        .decode("ascii")
        .rstrip("=")  # Remove padding
        .rstrip("A")
    )  # Remove 000000


class Singleton:
    __slots__ = ()
    __instance: ClassVar[Optional[Any]] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance


class CachedMeta(type):
    __cache: weakref.WeakKeyDictionary[object, weakref.ReferenceType[object]]

    def __new__(cls, name: str, bases: Any, classdict: Any) -> Any:
        result = super().__new__(cls, name, bases, classdict)
        result.__cache = weakref.WeakKeyDictionary()
        return result

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        instance = super().__call__(*args, **kwargs)
        return cls.__cache.setdefault(instance, weakref.ref(instance))()


@final
class Default(enum.Enum):
    sentinel = enum.auto()


@final
class Copy(enum.Enum):
    IDENTICAL = enum.auto()


def debug_repr(__obj: object) -> str:
    try:
        return str(__obj.__antidote_debug_repr__())  # type: ignore
    except Exception:
        pass

    if isinstance(__obj, type) or inspect.isfunction(__obj) or inspect.ismethod(__obj):
        if isinstance(__obj.__module__, str) and __obj.__module__ not in {"__main__", "builtins"}:
            module = __obj.__module__ + "."
        else:
            module = ""
        return f"{module}{__obj.__qualname__}"

    return repr(__obj)


def debug_repr_call(
    func: Callable[..., object], args: tuple[Any, ...], kwargs: dict[str, Any]
) -> str:
    out = [f"{debug_repr(func)}("]
    for arg in args:
        out.append(repr(arg))
        out.append(", ")
    for name, value in kwargs.items():
        out.append(f"{name}={value!r}")
        out.append(", ")
    if len(out) > 1:
        out[-1] = ")"
    else:
        out.append(")")
    return "".join(out)


def auto_detect_var_name(*, depth: int = 2, root: types.FrameType | None = None) -> str:
    root = inspect.currentframe() if root is None else root
    frame = root
    assert frame is not None
    n = depth
    while n > 0 and frame.f_back is not None:
        frame = frame.f_back
        n -= 1

    module_name = frame.f_globals.get("__name__", "__main__")
    lineno = frame.f_lineno

    # Happens with generics such as ScopeGlobalVar[T]()
    if module_name == "typing":
        return auto_detect_var_name(depth=depth + 1, root=root)

    instructions = iter(dis.get_instructions(frame.f_code))
    name: str | None = None
    # TODO: add coverage with Python 3.11 support
    for instruction in instructions:  # pragma: no cover
        if instruction.offset >= frame.f_lasti:
            if "STORE" in instruction.opname:
                name = instruction.argval
            else:
                instruction = next(instructions)
                if "STORE" in instruction.opname:
                    name = instruction.argval
            break

    if not isinstance(name, str) or not re.match(r"\w+", name):
        name = "<anonymous>"

    origin = f"{module_name}:{lineno}"
    return f"{name}@{origin}"


def auto_detect_origin_frame(*, depth: int = 2) -> str:
    frame = inspect.currentframe()
    assert frame is not None
    while depth > 0 and frame.f_back is not None:
        frame = frame.f_back
        depth -= 1

    # Happens in doctest that '__name__' isn't defined
    module_name = frame.f_globals.get("__name__", "__main__")
    lineno = frame.f_lineno
    return f"{module_name}:{lineno}"


def prepare_injection(
    *,
    inject: None | Default,
    catalog: Catalog,
    type_hints_locals: Mapping[str, object] | None,
    method: bool = False,
) -> Callable[[F], F]:
    if not (isinstance(inject, Default) or inject is None):
        raise TypeError(f"inject can only be None if specified, not a {type(inject)!r}")

    def prepare(wrapped: Any, do_injection: bool = inject is not None) -> Any:
        from ..core import DoubleInjectionError, inject

        try:
            if method:
                if do_injection:
                    wrapped = inject.method(
                        wrapped,
                        app_catalog=catalog,
                        type_hints_locals=type_hints_locals,
                    )
                else:
                    wrapped = inject.method(
                        wrapped, app_catalog=catalog, ignore_defaults=True, ignore_type_hints=True
                    )

            elif do_injection:
                wrapped = inject(wrapped, app_catalog=catalog, type_hints_locals=type_hints_locals)
        except DoubleInjectionError:
            inject.rewire(wrapped, app_catalog=catalog, method=method)

        return wrapped

    return prepare


def enforce_valid_name(name: str) -> None:
    if not isinstance(name, str):
        raise TypeError(f"name must be a string, not a {type(name)!r}")
    pattern = r"[\w-]+"
    if not re.match(pattern, name):
        raise ValueError(f"name must match the regex {pattern!r}")


# Imitates @functools.wraps
def wraps_frozen(__wrapped: object, signature: inspect.Signature | None = None) -> Callable[[T], T]:
    def f(wrapper: T) -> T:
        from ..core._raw import is_wrapper

        object.__setattr__(
            wrapper, "__wrapped__", __wrapped.__wrapped__ if is_wrapper(__wrapped) else __wrapped
        )

        if signature is not None:
            object.__setattr__(wrapper, "__signature__", signature)
        for attr in functools.WRAPPER_ASSIGNMENTS:
            object.__setattr__(wrapper, attr, getattr(__wrapped, attr))
        return wrapper

    return f


# For speed and space efficiency
EMPTY_TUPLE: tuple[Any, ...] = ()
EMPTY_DICT: dict[str, Any] = {}
