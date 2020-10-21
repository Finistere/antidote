"""
Similar to the pure Python, but used to have a cdef function for faster access.
"""
import threading
from contextlib import contextmanager
from typing import Callable

# @formatter:off
from antidote.core.container cimport RawContainer
# @formatter:on

cdef:
    RawContainer __container = None
    object __container_lock = threading.RLock()

cdef RawContainer fast_get_container():
    assert __container is not None
    return __container

def get_container() -> RawContainer:
    return fast_get_container()

def reset():
    global __container
    __container = None

def init():
    global __container
    if __container is None:
        with __container_lock:
            if __container is None:
                from .utils.world import new_container
                __container = new_container()

@contextmanager
def override(create: Callable[[RawContainer], RawContainer]):
    global __container
    with __container_lock:
        old = __container
        try:
            __container = create(old)
            yield
        finally:
            __container = old
