# @formatter:off
from cpython.ref cimport PyObject

from antidote._internal.stack cimport DependencyStack
# @formatter:on

# flags
cdef:
    size_t FLAG_DEFINED, FLAG_SINGLETON

cdef class DependencyInstance:
    cdef:
        readonly object instance
        readonly bint singleton

cdef class PyObjectBox:
    cdef:
        object obj

cdef struct DependencyResult:
    PyObject*box
    size_t flags

cdef struct ProviderCache:
    size_t length
    size_t capacity
    PyObject** dependencies
    size_t*counters
    PyObject** providers

cdef class DependencyContainer:
    cpdef object get(self, object dependency)
    cpdef DependencyInstance provide(self, object dependency)

cdef class RawDependencyContainer(DependencyContainer):
    cdef:
        DependencyStack __dependency_stack
        ProviderCache __cache
        list __providers
        dict __singletons
        bint __frozen
        object __singleton_lock
        object __freeze_lock
        unsigned long __singletons_clock
        object __weakref__

    cdef fast_get(self, PyObject*dependency, DependencyResult*result)
    cdef __safe_provide(self, PyObject*dependency, DependencyResult*result,
                        unsigned long singletons_clock)

cdef class RawDependencyProvider:
    cdef:
        object _container_ref

    cpdef DependencyInstance provide(self, object dependency,
                                     DependencyContainer container)
    cdef fast_provide(self, PyObject*dependency, PyObject*container,
                      DependencyResult*result)

cdef class FastDependencyProvider(RawDependencyProvider):
    pass
