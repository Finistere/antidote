from contextlib import contextmanager
from threading import RLock
from typing import Callable

from ..core import DependencyContainer

__container: DependencyContainer = None
__container_lock = RLock()
__overridden: int = 0


def is_overridden():
    return __overridden == 0


# Used only for tests, as the cython version does not have a "public" __container
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


def get_container() -> DependencyContainer:
    assert __container is not None
    return __container


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
