from typing import Dict

from .. import API


@API.private
class SlotsRepr:
    __slots__ = ()

    def __repr__(self) -> str:
        slots_attrs = []
        for cls in type(self).__mro__:
            for name in getattr(cls, '__slots__', []):
                attr = f"_{cls.__name__}{name}" if name.startswith('__') else name
                slots_attrs.append(f'{name}={getattr(self, attr)!r}')
        return f"{type(self).__name__}({', '.join(slots_attrs)})"


@API.private
class SlotRecord(SlotsRepr):
    """
    Used in similar fashion to data classes. Used whenever mutability is still needed
    """
    __slots__ = ()

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__()
        attrs: Dict[str, object] = dict(zip(self.__slots__, args))
        attrs.update(kwargs)
        for attr, value in attrs.items():
            setattr(self, attr, value)
