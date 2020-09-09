from itertools import chain
from typing import TypeVar

T = TypeVar('T')


class SlotsReprMixin:
    """
    Used by all classes using __slots__ to generate an helpful repr with all
    the defined fields.
    """
    __slots__ = ()

    def __repr__(self):
        slots_attrs = (
            f'{name}={getattr(self, name)!r}'
            for name in chain.from_iterable(getattr(cls, '__slots__', [])
                                            for cls in type(self).__mro__)
        )
        return f"{type(self).__name__}({', '.join(slots_attrs)})"


class FinalMeta(type):
    def __new__(cls, name, bases, classdict):
        for b in bases:
            if isinstance(b, FinalMeta):
                raise TypeError(f"Type '{b.__name__}' cannot be inherited.")
        return type.__new__(cls, name, bases, dict(classdict))


class API(metaclass=FinalMeta):

    @staticmethod
    def public(x: T) -> T:
        """
        Objects marked with this decorator are considered to be in the public API.
        Breaking changes will be avoided and will be taken into account in the
        semantic versioning.
        """
        return x

    @staticmethod
    def experimental(x: T) -> T:
        """
        Similar to public, they're part of the public API. However it's considered
        experimental, so the next major version change has a higher change of introducing
        changes.
        """
        return x

    @staticmethod
    def public_for_tests(x: T) -> T:
        """
        Similar to public, they're part of the public API. However they're only meant to
        be used in tests.
        """
        return x

    @staticmethod
    def private(x: T) -> T:
        """
        Only for internal use. They're are NOT part of the public API, and as such may
        change without warning in later versions. If you need access to private APIs,
        please submit an issue.
        """
        return x
