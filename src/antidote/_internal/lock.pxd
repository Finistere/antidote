# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
# Based on FastRLock implemented by Stefan Behnel
# https://code.activestate.com/recipes/577336-fast-re-entrant-optimistic-lock-implemented-in-cyt/
from cpython cimport pythread

cdef class FastRLock:
    cdef:
        pythread.PyThread_type_lock _real_lock
        long _owner  # ID of thread owning the lock
        int _count  # re-entry count
        int _pending_requests  # number of pending requests for real lock
        bint _is_locked  # whether the real lock is acquired

    cpdef bint acquire(self)

    cpdef release(self)
