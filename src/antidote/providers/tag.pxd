# cython: language_level=3
# cython: boundscheck=False, wraparound=False
from antidote.core.container cimport DependencyContainer, DependencyInstance, DependencyProvider

cdef class Tag:
    cdef:
        readonly str name
        readonly dict _attrs

cdef class Tagged:
    cdef:
        readonly str name

cdef class TaggedDependencies:
    cdef:
        DependencyContainer _container
        object _lock
        list _dependencies
        list _tags
        list _instances

cdef class TagProvider(DependencyProvider):
    cdef:
        dict _dependency_to_tag_by_tag_name

    cpdef DependencyInstance provide(self, dependency)
