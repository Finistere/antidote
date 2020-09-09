# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False

# @formatter:off
import threading
from typing import Callable

from antidote.core.container cimport DependencyContainer
# @formatter:on

from contextlib import contextmanager

cdef:
    DependencyContainer __container = None
    object __container_lock = threading.RLock()
    unsigned int __overridden = 0

cpdef DependencyContainer get_container():
    assert __container is not None
    return __container

def is_overridden():
    return __overridden == 0

def reset():
    global __container
    __container = None

def init():
    global __container
    if __container is None:
        with __container_lock:
            if __container is None:
                from . import defaults
                __container = defaults.new_container()

@contextmanager
def override(create: Callable[[DependencyContainer], DependencyContainer]):
    global __container, __overridden
    with __container_lock:
        old = __container
        try:
            __overridden += 1
            __container = create(old)
            yield
        finally:
            __container = old
            __overridden -= 1
