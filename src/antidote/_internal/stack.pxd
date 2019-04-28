# cython: language_level=3
# cython: boundscheck=False, wraparound=False

cdef class DependencyStack:
    cdef:
        list _stack
        set _seen

    cdef bint push(self, object dependency)
    cdef pop(self)
