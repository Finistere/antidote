# cython: language_level=3
# cython: boundscheck=False, wraparound=False
from antidote.core.container cimport DependencyInstance, DependencyProvider

cdef class FactoryProvider(DependencyProvider):
    cdef:
        dict _builders

    cpdef DependencyInstance provide(self, object dependency)

cdef class Build:
    cdef:
        readonly object dependency
        readonly dict kwargs
        int _hash
