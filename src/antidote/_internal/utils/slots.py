from .. import API


@API.private
class SlotsRepr:
    __slots__ = ()

    def __repr__(self):
        slots_attrs = []
        for cls in type(self).__mro__:
            for name in getattr(cls, '__slots__', []):
                attr = f"_{cls.__name__}{name}" if name.startswith('__') else name
                slots_attrs.append(f'{name}={getattr(self, attr)!r}')
        return f"{type(self).__name__}({', '.join(slots_attrs)})"


@API.private
class SlotsCopy:
    __slots__ = ()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def copy(self, **kwargs):
        return type(self)(**{
            name: kwargs.get(name, getattr(self, name))
            for cls in type(self).__mro__
            for name in getattr(cls, '__slots__', [])
        })


@API.private
class SlotRecord(SlotsRepr, SlotsCopy):
    """
    Used in similar fashion to data classes. Used whenever mutability is still needed
    """
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        super().__init__()
        attrs = dict(zip(self.__slots__, args))
        attrs.update(kwargs)
        for attr, value in attrs.items():
            setattr(self, attr, value)

    def copy(self, **kwargs):
        return type(self)(**{
            name: kwargs.get(name, getattr(self, name))
            for cls in type(self).__mro__
            for name in getattr(cls, '__slots__', [])
        })
