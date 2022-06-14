from __future__ import annotations

import dis
import inspect
import textwrap
import types
from dataclasses import dataclass
from typing import Generic, TypeVar

from typing_extensions import final

from antidote._internal.utils import short_id

T = TypeVar("T")


@final
@dataclass(frozen=True, eq=True, unsafe_hash=True)
class Box(Generic[T]):
    value: T

    def __repr__(self) -> str:
        return f"Box({self.value!r})@{short_id(self)}"


class Obj:
    """
    Inspired from https://stackoverflow.com/a/41586688
    The goal is just
    """

    def __init__(self) -> None:
        frame: types.FrameType = inspect.currentframe().f_back  # type: ignore
        instructions = iter(dis.get_instructions(frame.f_code))
        for instruction in instructions:
            if instruction.offset == frame.f_lasti:
                break
        self.__name = next(instructions).argval

    def __repr__(self) -> str:
        return f"{self.__name}@{short_id(self)}"


def expected_debug(__value: str, *, legend: bool = True) -> str:
    if __value.startswith("\n"):
        __value = textwrap.dedent(__value[1:])
    lines = __value.splitlines(keepends=True)
    while not lines[-1].strip():
        lines.pop()

    if legend:
        from antidote.core._debug import _LEGEND  # pyright: ignore[reportPrivateUsage]

        lines.append(_LEGEND)

    return "".join(lines)
