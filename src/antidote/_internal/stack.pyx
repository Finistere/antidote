from contextlib import contextmanager
from typing import Hashable

# @formatter:off
cimport cython
from cpython.mem cimport PyMem_Free, PyMem_Malloc, PyMem_Realloc
from cpython.object cimport PyObject
# @formatter:on

cdef extern from "Python.h":
    Py_hash_t PyObject_Hash(PyObject *o)


@cython.final
cdef class DependencyStack:
    """
    Cython implementation of the DependencyStack with the same Python API.

    It relies on an array of hashes which is faster than a set for a low depth.
    """

    def __init__(self):
        cdef:
            size_t capacity = 32

        self._trace = <PyObject**> PyMem_Malloc(capacity * sizeof(PyObject*))
        self._hashes = <Py_hash_t*> PyMem_Malloc(capacity * sizeof(Py_hash_t))
        self._depth = 0
        self._capacity = capacity

    def __dealloc__(self):
        PyMem_Free(self._trace)
        PyMem_Free(self._hashes)

    @contextmanager
    def instantiating(self, dependency: Hashable):
        if 0 != self.push(<PyObject*> dependency):
            raise self.reset_with_error(<PyObject*> dependency)
        try:
            yield
        finally:
            self.pop()

    @property
    def depth(self):
        return self._depth

    def to_list(self):
        cdef:
            list l = []
            PyObject*t

        for t in self._trace[:self._depth]:
            l.append(<object> t)

        return l

    cdef Exception reset_with_error(self, PyObject*dependency):
        cdef:
            list l = []
            PyObject*t

        for t in self._trace[:self._depth]:
            l.append(<object> t)
        l.append(<object> dependency)

        from ..core.exceptions import DependencyCycleError
        return DependencyCycleError(l)

    cdef bint push(self, PyObject*dependency):
        """
        Args:
            dependency: supposed to be hashable as the core tries to 
                retrieves from a dictionary first. 

        Returns:
            0 OK
            1 if present in the stack
        """
        cdef:
            size_t depth = self._depth
            PyObject** traces = self._trace
            Py_hash_t*hashes = self._hashes
            Py_hash_t*h
            Py_hash_t dependency_hash = PyObject_Hash(dependency)
            int i = 0
            PyObject*t

        for h in hashes[:depth]:
            if h[0] == dependency_hash:
                t = traces[i]
                if dependency == t or <object> dependency == <object> t:
                    return 1
            i += 1

        if depth == self._capacity:
            self._capacity *= 2
            PyMem_Realloc(hashes, self._capacity * sizeof(Py_hash_t))
            PyMem_Realloc(traces, self._capacity * sizeof(PyObject*))
        hashes[depth] = dependency_hash
        traces[depth] = dependency

        self._depth += 1

        return 0

    cdef void pop(self):
        """
        Latest elements of the stack is removed.
        """
        self._depth -= 1
