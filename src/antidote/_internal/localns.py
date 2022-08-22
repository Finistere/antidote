from __future__ import annotations

import inspect
from typing import Mapping, Optional, TYPE_CHECKING

from .config import config
from .utils import Default

if TYPE_CHECKING:
    from ..core import TypeHintsLocals


def retrieve_or_validate_injection_locals(
    type_hints_locals: TypeHintsLocals,
) -> Optional[Mapping[str, object]]:

    if type_hints_locals is Default.sentinel:
        type_hints_locals = "auto" if config.auto_detect_type_hints_locals else None

    if type_hints_locals == "auto":
        frame = inspect.currentframe()
        # In theory this shouldn't be possible
        if frame is None or frame.f_back is None or frame.f_back.f_back is None:  # pragma: no cover
            return {}

        frame = frame.f_back.f_back
        first_level_locals = frame.f_locals
        qualname = first_level_locals.get("__qualname__")
        # If inside class namespace, trying to retrieve all locals.
        if isinstance(qualname, str) and "<locals>" in qualname:
            localns: dict[str, object] = {}
            parts = qualname.split(".")
            all_localns = [first_level_locals]
            while parts.pop() != "<locals>" and frame.f_back is not None:
                frame = frame.f_back
                all_localns.append(frame.f_locals)
            for x in reversed(all_localns):
                localns.update(x)
            return localns
        return first_level_locals
    elif not (type_hints_locals is None or isinstance(type_hints_locals, dict)):
        raise TypeError(
            f"If specified, type_hints_locals must be None, a dict or the literal "
            f"'auto', not a {type(type_hints_locals)!r}"
        )
    return type_hints_locals
