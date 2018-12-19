# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
# cython: linetrace=True
# noinspection PyUnresolvedReferences
from ..container cimport Dependency, Instance, Provider

cdef class FactoryProvider(Provider):
    cdef:
        dict _factories

    cpdef Instance provide(self, Dependency dependency)

cdef class Build(Dependency):
    cdef:
        public tuple args
        public dict kwargs
