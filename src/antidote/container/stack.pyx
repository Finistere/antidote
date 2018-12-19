# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
# cython: linetrace=True
from contextlib import contextmanager

# @formatter:off
cimport cython
from cpython.set cimport PySet_Contains

from ..exceptions import DependencyCycleError
# @formatter:on

# Final class as its behavior can only be changed through a Cython class.
@cython.final
cdef class InstantiationStack:
    def __init__(self):
        self._stack = list()
        self._seen = set()

    @contextmanager
    def instantiating(self, dependency_id):
        if 1 != self.push(dependency_id):
            raise DependencyCycleError(self._stack.copy() + [dependency_id])
        try:
            yield
        finally:
            self.pop()

    cdef bint push(self, object dependency_id):
        """
        Args:
            dependency_id: supposed to be hashable as the container tries to 
                retrieves from a dictionary first. 

        Returns:
            0 if present in the stack
            1 OK
        """
        cdef:
            list stack
            bint seen

        if 1 == PySet_Contains(self._seen, dependency_id):
            return 0

        self._stack.append(dependency_id)
        self._seen.add(dependency_id)
        return 1

    cdef pop(self):
        """
        Latest elements of the stack is removed.
        """
        self._seen.remove(self._stack.pop())
