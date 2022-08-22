from dataclasses import dataclass

from typing_extensions import final

from . import API
from .utils import Singleton


@API.private
@final
@dataclass(eq=False)
class ConfigImpl(Singleton):
    __slots__ = ("_auto_detect_type_hints_locals",)
    _auto_detect_type_hints_locals: bool

    def __init__(self) -> None:
        object.__setattr__(self, "_auto_detect_type_hints_locals", False)

    @property
    def auto_detect_type_hints_locals(self) -> bool:
        return self._auto_detect_type_hints_locals

    @auto_detect_type_hints_locals.setter
    def auto_detect_type_hints_locals(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError(
                f"auto_detect_type_hints_locals must be a boolean, not a {type(value)}."
            )
        object.__setattr__(self, "_auto_detect_type_hints_locals", value)


config = ConfigImpl()
