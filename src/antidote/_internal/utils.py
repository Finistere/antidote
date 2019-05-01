from itertools import chain


class SlotsReprMixin:
    """
    Used by all classes using __slots__ to generate an helpful repr with all
    the defined fields.
    """
    __slots__ = ()

    def __repr__(self):
        slots = chain.from_iterable(getattr(cls, '__slots__', [])
                                    for cls in type(self).__mro__)
        return "{type}({slots})".format(
            type=type(self).__name__,
            slots=', '.join((
                '{}={!r}'.format(name, getattr(self, name))
                for name in slots
            ))
        )
