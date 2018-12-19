# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
# cython: linetrace=True
from typing import (Callable, TypeVar, Union)

# @formatter:off
# noinspection PyUnresolvedReferences
from ...container cimport Dependency, DependencyContainer, Instance, Provider
# @formatter:on

T = TypeVar('T')

cdef class Tag:
    def __init__(self, name: str, **attrs):
        self.name = name
        self._attrs = attrs

    def __repr__(self):
        return "{}(name={!r}, **attrs={!r})".format(type(self).__name__,
                                                    self.id,
                                                    self._attrs)

    def __getattr__(self, item):
        return self._attrs.get(item)

cdef class Tagged(Dependency):
    def __init__(self, name: str, filter: Union[Callable[[Tag], bool]] = None):
        # If filter is None -> caching works.
        # If not, dependencies are still cached if necessary.
        super().__init__(name)
        if filter is not None and not callable(filter):
            raise ValueError("filter must be either a function or None")

        self.filter = filter or (lambda _: True)  # type: Callable[[Tag], bool]

    def __repr__(self):
        return "{}(name={!r}, filter={!r})".format(type(self).__name__,
                                                   self.id,
                                                   self.filter)

    @property
    def name(self) -> str:
        return self.id

    def __hash__(self):
        return object.__hash__(self)

    def __eq__(self, object other):
        return object.__eq__(self, other)
