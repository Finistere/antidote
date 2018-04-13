import threading
import time

import random

from antidote import DependencyManager


class Service(object):
    pass


class AnotherService(object):
    pass


def test_instantiation_safety():
    n_threads = 10
    manager = DependencyManager()

    class Service(object):
        pass

    class AnotherService(object):
        pass

    def service_factory():
        time.sleep(random.random() * .1 + .1)
        return Service()

    def another_service_factory():
        time.sleep(random.random() * .1 + .1)
        return AnotherService()

    manager.factory(service_factory, dependency_id=Service, singleton=True)
    manager.factory(another_service_factory, dependency_id=AnotherService,
                    singleton=False)

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
