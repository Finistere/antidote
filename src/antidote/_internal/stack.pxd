from cpython.object cimport PyObject

ctypedef Py_ssize_t Py_hash_t

cdef class DependencyStack:
    cdef:
        PyObject** _trace
        Py_hash_t* _hashes
        size_t _depth
        size_t _capacity

    cdef Exception reset_with_error(self, PyObject* dependency)
    cdef bint push(self, PyObject* dependency)
    cdef void pop(self)
