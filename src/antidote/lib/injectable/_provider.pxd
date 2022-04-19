cdef class Parameterized:
    cdef:
        readonly object wrapped
        readonly dict parameters
        int _hash
