import threading
import time

import random

from antidote import DependencyManager


class Service(object):
    pass


class AnotherService(object):
    pass


def make_delayed_factory(a, b, factory):
    def f():
        time.sleep(a + b * random.random())
        return factory()

    return f


def test_instantiation_safety():
    n_threads = 10
    manager = DependencyManager()

    manager.factory(
        make_delayed_factory(.1, .1, Service),
        dependency_id=Service,
        singleton=True
    )
    manager.factory(
        make_delayed_factory(.1, .1, AnotherService),
        dependency_id=AnotherService,
        singleton=False
    )

    singleton_got = []
    non_singleton_got = []

    def worker():
        singleton_got.append(manager.container[Service])
        non_singleton_got.append(manager.container[AnotherService])

    threads = [
        threading.Thread(target=worker)
        for _ in range(n_threads)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert 1 == len(set(singleton_got))
    assert n_threads == len(set(non_singleton_got))
