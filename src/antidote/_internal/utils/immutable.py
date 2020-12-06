import inspect
from typing import Dict

from .slots import SlotsRepr
from .. import API
from ..._compatibility.typing import GenericMeta


@API.private
class ImmutableMeta(type):
    def __new__(mcls, name, bases, namespace, abstract: bool = False, **kwargs):
        if '__slots__' not in namespace:
            raise TypeError("Attributes must be defined in slots")
        slots = set(namespace['__slots__'])
        if any(name.startswith('__') for name in slots):
            raise ValueError("Private attributes are not supported.")

        if abstract:
            if len(slots) > 0:
                raise ValueError("Cannot be abstract and have a non-empty __slots__")

        # TODO: Type ignore necessary when type checking with Python 3.6
        #       To be removed ASAP.
        return super().__new__(mcls, name, bases, namespace, **kwargs)  # type: ignore


# TODO: remove after Python 3.6 support drops.
@API.private
class ImmutableGenericMeta(ImmutableMeta, GenericMeta):
    pass


@API.private
class Immutable(SlotsRepr, metaclass=ImmutableMeta, abstract=True):
    """
    Imitates immutable behavior by raising an exception when modifying an
    attribute through the standard means.
    """
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        # quick way to initialize an Immutable through args. It won't take into
        # account parent classes though.
        attrs: Dict[str, object] = dict(zip(self.__slots__, args))
        attrs.update(kwargs)
        for attr, value in attrs.items():
            object.__setattr__(self, attr, value)

    def __setattr__(self, name, value):
        raise AttributeError(f"{type(self)} is immutable")


@API.private
class FinalImmutableMeta(ImmutableMeta):
    def __new__(mcls, name, bases, namespace, **kwargs):
        for b in bases:
            if isinstance(b, ImmutableMeta) \
                    and b.__module__ != __name__:
                raise TypeError(f"Type '{b.__name__}' cannot be inherited by {name}.")

        return super().__new__(mcls, name, bases, namespace, **kwargs)


@API.private
class FinalImmutable(Immutable, metaclass=FinalImmutableMeta, abstract=True):
    __slots__ = ()
