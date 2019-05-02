# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False
from contextlib import contextmanager
from typing import Hashable

# @formatter:off
cimport cython
from cpython.set cimport PySet_Contains

from ..exceptions import DependencyCycleError
# @formatter:on

# Final class as its behavior can only be changed through a Cython class. The
# DependencyContainer calls directly push() and pop()
@cython.final
cdef class DependencyStack:
    def __init__(self):
        self._stack = list()
        self._seen = set()

    @contextmanager
    def instantiating(self, dependency: Hashable):
        if 1 != self.push(dependency):
            raise DependencyCycleError(self._stack.copy() + [dependency])
        try:
            yield
        finally:
            self.pop()

    cdef bint push(self, object dependency):
        """
        Args:
            dependency: supposed to be hashable as the core tries to 
                retrieves from a dictionary first. 

        Returns:
            0 if present in the stack
            1 OK
        """
        cdef:
            list stack
            bint seen

        if 1 == PySet_Contains(self._seen, dependency):
            return 0

        self._stack.append(dependency)
        self._seen.add(dependency)
        return 1

    cdef pop(self):
        """
        Latest elements of the stack is removed.
        """
        self._seen.remove(self._stack.pop())
