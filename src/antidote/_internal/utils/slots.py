from typing import Protocol

from antidote._internal import API


@API.private
class SlotsInitProtocol(Protocol):
    def __init__(self, **kwargs):
        pass  # pragma: no cover


@API.private
class SlotsMixin:
    __slots__ = ()

    def __repr__(self):
        slots_attrs = []
        for cls in type(self).__mro__:
            for name in getattr(cls, '__slots__', []):
                attr = f"_{cls.__name__}{name}" if name.startswith('__') else name
                slots_attrs.append(f'{name}={getattr(self, attr)!r}')
        return f"{type(self).__name__}({', '.join(slots_attrs)})"

    def copy(self: SlotsInitProtocol, **kwargs):
        return type(self)(**{
            name: kwargs.get(name, getattr(self, name))
            for cls in type(self).__mro__
            for name in getattr(cls, '__slots__', [])
        })


@API.private
class SlotRecord(SlotsMixin):
    """
    Used in similar fashion to data classes. Used whenever mutability is still needed
    """
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        attrs = dict(zip(self.__slots__, args))
        attrs.update(kwargs)
        for attr, value in attrs.items():
            setattr(self, attr, value)
