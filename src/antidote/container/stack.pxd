# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
# cython: linetrace=True

cdef class InstantiationStack:
    cdef:
        list _stack
        set _seen

    cdef bint push(self, object dependency_id)
    cdef pop(self)
