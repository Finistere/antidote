# cython: language_level=3
# cython: boundscheck=False, wraparound=False
from antidote.core.container cimport DependencyInstance, DependencyProvider

cdef class IndirectProvider(DependencyProvider):
    cdef:
        dict _stateful_links
        dict _links

    cpdef DependencyInstance provide(self, object dependency)
