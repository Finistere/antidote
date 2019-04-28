# cython: language_level=3
# cython: boundscheck=False, wraparound=False
from antidote.core.container cimport DependencyInstance, DependencyProvider

cdef class LazyCallProvider(DependencyProvider):
    cpdef DependencyInstance provide(self, object dependency)

cdef class LazyCall:
    cdef:
        object _func
        tuple _args
        dict _kwargs
        bint _singleton

cdef class LazyMethodCall:
    cdef:
        str _method_name
        bint _singleton
        tuple _args
        dict _kwargs
        str _key

    cdef object _call(self, object instance)
