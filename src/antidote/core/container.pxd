# cython: language_level=3
# cython: boundscheck=False, wraparound=False
# @formatter:off
from cpython.ref cimport PyObject

from antidote._internal.stack cimport DependencyStack
# @formatter:on

# flags
cdef:
    int FLAG_DEFINED, FLAG_SINGLETON

cdef class DependencyInstance:
    cdef:
        readonly object instance
        readonly bint singleton

    cdef DependencyInstance copy(self)

cdef class PyObjectBox:
    cdef:
        object obj

cdef struct DependencyResult:
    PyObject* box
    int flags

cdef struct ProviderCache:
    size_t length
    size_t capacity
    PyObject** dependencies
    size_t* counters
    PyObject** providers

cdef class DependencyContainer:
    cdef:
        list __providers
        dict __singletons
        bint __frozen
        DependencyStack __dependency_stack
        object __instantiation_lock
        unsigned long __singletons_clock
        ProviderCache __cache

    cpdef object get(self, object dependency)
    cpdef DependencyInstance provide(self, object dependency)
    cdef fast_get(self, PyObject* dependency, DependencyResult* result)
    cdef __safe_provide(self, PyObject* dependency, DependencyResult* result, unsigned long singletons_clock)

cdef class DependencyProvider:
    cdef fast_provide(self, PyObject* dependency, PyObject* container, DependencyResult* result)
    cpdef DependencyInstance provide(self, object dependency, DependencyContainer container)

cdef class FastDependencyProvider(DependencyProvider):
    pass
