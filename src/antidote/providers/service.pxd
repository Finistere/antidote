# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
from antidote.core.container cimport DependencyInstance, DependencyProvider

cdef class ServiceProvider(DependencyProvider):
    cdef:
        dict _service_to_factory

    cpdef DependencyInstance provide(self, object dependency)

cdef class Build:
    cdef:
        readonly object wrapped
        readonly tuple args
        readonly dict kwargs
