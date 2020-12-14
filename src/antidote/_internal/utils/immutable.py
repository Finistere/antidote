from typing import cast, Dict, Iterable, Tuple, Type

from .slots import SlotsRepr
from .. import API
from ..._compatibility.typing import GenericMeta


@API.private
class ImmutableMeta(type):
    def __new__(mcs: 'Type[ImmutableMeta]',
                name: str,
                bases: Tuple[type, ...],
                namespace: Dict[str, object],
                **kwargs: object
                ) -> 'ImmutableMeta':
        if '__slots__' not in namespace:
            raise TypeError("Attributes must be defined in slots")

        slots = set(cast(Iterable[str], namespace['__slots__']))
        if any(name.startswith('__') for name in slots):
            raise ValueError("Private attributes are not supported.")

        # TODO: Type ignore necessary when type checking with Python 3.6
        #       To be removed ASAP.
        return cast(
            ImmutableMeta,
            super().__new__(mcs, name, bases, namespace, **kwargs)  # type: ignore
        )


# TODO: remove after Python 3.6 support drops.
@API.private
class ImmutableGenericMeta(ImmutableMeta, GenericMeta):
    pass


@API.private
class Immutable(SlotsRepr, metaclass=ImmutableMeta):
    """
    Imitates immutable behavior by raising an exception when modifying an
    attribute through the standard means.
    """
    __slots__ = ()

    def __init__(self, *args: object, **kwargs: object) -> None:
        # quick way to initialize an Immutable through args. It won't take into
        # account parent classes though.
        attrs: Dict[str, object] = dict(zip(self.__slots__, args))
        attrs.update(kwargs)
        for attr, value in attrs.items():
            object.__setattr__(self, attr, value)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self)} is immutable")


@API.private
class FinalImmutableMeta(ImmutableMeta):
    def __new__(mcs: 'Type[FinalImmutableMeta]',
                name: str,
                bases: Tuple[type, ...],
                namespace: Dict[str, object]
                ) -> 'FinalImmutableMeta':

        for b in bases:
            if isinstance(b, FinalImmutableMeta) and b.__module__ != __name__:
                raise TypeError(f"Type '{b.__name__}' cannot be inherited by {name}.")

        return cast(FinalImmutableMeta, super().__new__(mcs, name, bases, namespace))


@API.private
class FinalImmutable(Immutable, metaclass=FinalImmutableMeta):
    __slots__ = ()
