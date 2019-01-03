# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
from antidote.core.container cimport DependencyInstance, DependencyProvider

cdef class ResourceProvider(DependencyProvider):
    cdef:
        dict _priority_sorted_resources_by_namespace

    cpdef DependencyInstance provide(self, object dependency)
