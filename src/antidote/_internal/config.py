from typing_extensions import final

from . import API
from .utils import Singleton


@API.private
@final
class ConfigImpl(Singleton):
    __slots__ = ("_auto_detect_type_hints_locals", "__dict__")

    @property
    def auto_detect_type_hints_locals(self) -> bool:
        return bool(getattr(self, "_auto_detect_type_hints_locals", False))

    @auto_detect_type_hints_locals.setter
    def auto_detect_type_hints_locals(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError(
                f"auto_detect_type_hints_locals must be a boolean, not a {type(value)}."
            )
        setattr(self, "_auto_detect_type_hints_locals", value)
