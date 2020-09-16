"""
Similar to the pure Python, but used to have a cdef function for faster access.
"""
import threading
from contextlib import contextmanager
from typing import Callable

# @formatter:off
from antidote.core.container cimport RawDependencyContainer
# @formatter:on

cdef:
    RawDependencyContainer __container = None
    object __container_lock = threading.RLock()

cdef RawDependencyContainer fast_get_container():
    assert __container is not None
    return __container

def get_container() -> RawDependencyContainer:
    return fast_get_container()

def reset():
    global __container
    __container = None

def init():
    global __container
    if __container is None:
        with __container_lock:
            if __container is None:
                from . import container_utils
                __container = container_utils.new_container()

@contextmanager
def override(create: Callable[[RawDependencyContainer], RawDependencyContainer]):
    global __container
    with __container_lock:
        old = __container
        try:
            __container = create(old)
            yield
        finally:
            __container = old
