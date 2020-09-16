import enum

from .immutable import FinalImmutable, Immutable
from .meta import AbstractMeta, FinalMeta
from .slots import SlotRecord
from .. import API


@API.private
class Copy(enum.Enum):
    IDENTICAL = object()


@API.private
def raw_getattr(cls: type, attr: str, with_super: bool):
    """
    Used to retrieve the 'raw' attribute from a class, typically the descriptor itself
    and not whatever it outputs.

    Args:
        cls: Class from which an attribute must be retrieved
        attr: Name of the attribute
        with_super: Whether the attribute must be search in the whole inheritance
        hierarchy or not.

    Returns:
        The attribute or raises a KeyError.
    """
    if with_super:
        for c in cls.__mro__:
            try:
                return c.__dict__[attr]
            except KeyError:
                pass

        raise AttributeError(f"{cls} has no attribute '{attr}'")
    else:
        try:
            return cls.__dict__[attr]
        except KeyError:
            pass
        raise AttributeError(
            f"Attribute '{attr}' is not defined in {cls}. "
            f"Mother classes are not taken into account. "
            f"This may indicate that 'wire_super' is not configured properly.")
