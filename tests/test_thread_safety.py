import threading
import time
import random


from antidote import DependencyContainer


class Service(object):
    pass


class AnotherService(object):
    pass


def test_instantiation_safety():
    n_threads = 10
    container = DependencyContainer()

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

    container.register(service_factory, id=Service, singleton=True)
    container.register(another_service_factory, id=AnotherService,
                       singleton=False)

    singleton_got = []
    non_singleton_got = []

    def worker():
        singleton_got.append(container[Service])
        non_singleton_got.append(container[AnotherService])

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
