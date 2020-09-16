"""
Antidote has a global container which is managed in this module.
"""
import threading
from contextlib import contextmanager
from typing import Callable

from ..core.container import RawDependencyContainer

__container: RawDependencyContainer = None
__container_lock = threading.RLock()


# Used only for tests
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


def get_container() -> RawDependencyContainer:
    assert __container is not None
    return __container


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
