# cython: language_level=3
# cython: boundscheck=False, wraparound=False
from antidote.core.container cimport DependencyInstance, DependencyProvider

cdef class FactoryProvider(DependencyProvider):
    cdef:
        dict _builders

    cpdef DependencyInstance provide(self, object dependency)

cdef class Build:
    cdef:
        readonly object wrapped
        readonly tuple args
        readonly dict kwargs
        int _hash
