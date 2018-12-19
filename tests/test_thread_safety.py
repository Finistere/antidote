import random
import threading
import time

import pytest

from antidote import Tagged, TaggedDependencies
from antidote.helpers import factory, new_container


class Service:
    pass


class AnotherService:
    pass


def make_delayed_factory(factory_, a=0.01, b=0.01):
    def f():
        time.sleep(a + b * random.random())
        return factory_()

    return f


@pytest.fixture()
def container():
    c = new_container()
    c.update({Service: Service(), 'parameter': object()})

    return c


def multi_thread_do(target, n_threads=10):
    threads = [threading.Thread(target=target)
               for _ in range(n_threads)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()


def test_container_instantiation_safety(container):
    n_threads = 10

    factory(make_delayed_factory(Service),
            dependency_id=Service,
            singleton=True,
            container=container)
    factory(make_delayed_factory(AnotherService),
            dependency_id=AnotherService,
            singleton=False,
            container=container)

    singleton_got = []
    non_singleton_got = []

    def worker():
        singleton_got.append(container[Service])
        non_singleton_got.append(container[AnotherService])

    multi_thread_do(worker, n_threads)

    assert 1 == len(set(singleton_got))
    assert n_threads == len(set(non_singleton_got))


def test_tagged_dependencies_instantiation_safety(container):
    n_dependencies = 40

    for i in range(n_dependencies):
        factory(make_delayed_factory(object),
                dependency_id=i + 1,
                singleton=False,
                tags=['test'],
                container=container)

    tagged = container[Tagged('test')]  # type: TaggedDependencies
    dependencies = []

    def worker():
        for i, dep in enumerate(tagged.dependencies()):
            dependencies.append((i, dep))

    multi_thread_do(worker)

    assert n_dependencies == len(set(dependencies))
    assert set(dependencies) == set(enumerate(tagged.dependencies()))
