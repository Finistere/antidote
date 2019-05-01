# cython: language_level=3
# cython: boundscheck=False, wraparound=False
# @formatter:off
from antidote._internal.stack cimport DependencyStack
# @formatter:on

cdef class DependencyInstance:
    cdef:
        readonly object instance
        readonly bint singleton

cdef class DependencyContainer:
    cdef:
        object __weakref__
        list _providers
        dict _type_to_provider
        dict _singletons
        DependencyStack _dependency_stack
        object _instantiation_lock

    cpdef object get(self, object dependency)
    cpdef DependencyInstance safe_provide(self, object dependency)
    cpdef DependencyInstance provide(self, object dependency)

cdef class DependencyProvider:
    cdef:
        public DependencyContainer _container

    cpdef DependencyInstance provide(self, object dependency)

cdef class Lazy:
    cdef:
        public object dependency
