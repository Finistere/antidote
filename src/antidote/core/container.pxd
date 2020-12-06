# @formatter:off
from cpython.ref cimport PyObject

from antidote._internal.stack cimport DependencyStack
# @formatter:on

# flags
cdef:
    size_t FLAG_DEFINED, FLAG_SINGLETON

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

cdef class DependencyInstance:
    cdef:
        readonly bint singleton
        readonly object value

cdef class Container:
    pass

cdef class RawContainer(Container):
    cdef:
        list _providers
        dict _singletons
        object _singleton_lock
        unsigned long _singletons_clock
        DependencyStack _dependency_stack
        ProviderCache __cache
        bint __frozen
        object __freeze_lock
        object __weakref__

    cdef fast_get(self, PyObject*dependency, DependencyResult*result)
    cdef __safe_provide(self, PyObject*dependency, DependencyResult*result,
                        unsigned long singletons_clock)

cdef class RawProvider:
    cdef:
        object _container_ref

    cdef fast_provide(self, PyObject*dependency, PyObject*container,
                      DependencyResult*result)

cdef class FastProvider(RawProvider):
    pass
