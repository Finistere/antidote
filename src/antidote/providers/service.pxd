cdef class Build:
    cdef:
        readonly object dependency
        readonly dict kwargs
        readonly int _hash
