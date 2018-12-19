from typing import (Callable, TypeVar, Union)

from ..._internal.utils import SlotReprMixin
from ...container import Dependency

T = TypeVar('T')


class Tag(SlotReprMixin):
    __slots__ = ('name', '_attrs')

    def __init__(self, name: str, **attrs):
        self.name = name
        self._attrs = attrs

    def __getattr__(self, item):
        return self._attrs.get(item)


class Tagged(Dependency):
    __slots__ = ('filter',)

    def __init__(self, name: str, filter: Union[Callable[[Tag], bool]] = None):
        # If filter is None -> caching works.
        # If not, dependencies are still cached if necessary.
        super().__init__(name)
        if filter is not None and not callable(filter):
            raise ValueError("filter must be either a function or None")

        self.filter = filter or (lambda _: True)  # type: Callable[[Tag], bool]

    @property
    def name(self) -> str:
        return self.id

    def __hash__(self):
        return object.__hash__(self)

    def __eq__(self, other):
        return object.__eq__(self, other)
