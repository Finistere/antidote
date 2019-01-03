# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
# @formatter:off
from antidote._internal.lock cimport FastRLock
from antidote._internal.stack cimport DependencyStack
# @formatter:on

cdef class DependencyInstance:
    cdef:
        readonly object instance
        readonly bint singleton

cdef class DependencyContainer:
    cdef:
        readonly object SENTINEL
        object __weakref__
        list _providers
        dict _type_to_provider
        dict _singletons
        DependencyStack _dependency_stack
        FastRLock _instantiation_lock

    cpdef object provide(self, object dependency)

cdef class DependencyProvider:
    cdef:
        public DependencyContainer _container

    cpdef DependencyInstance provide(self, object dependency)

cdef class Lazy:
    cdef:
        public object dependency
