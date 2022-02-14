from __future__ import annotations

from .. import API


@API.private
class SlotsRepr:
    __slots__ = ()

    def __repr__(self) -> str:
        slots_attrs: list[str] = []
        for cls in type(self).__mro__:
            for name in getattr(cls, '__slots__', []):
                attr = f"_{cls.__name__}{name}" if name.startswith('__') else name
                slots_attrs.append(f'{name}={getattr(self, attr)!r}')
        return f"{type(self).__name__}({', '.join(slots_attrs)})"
