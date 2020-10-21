"""
Antidote has a global container which is managed in this module.
"""
import threading
from contextlib import contextmanager
from typing import Callable, Optional

from ..core.container import RawContainer

__container: Optional[RawContainer] = None
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


def get_container() -> RawContainer:
    assert __container is not None
    return __container


@contextmanager
def override(create: Callable[[RawContainer], RawContainer]):
    global __container
    with __container_lock:
        assert __container is not None
        old = __container
        try:
            __container = create(old)
            yield
        finally:
            __container = old
