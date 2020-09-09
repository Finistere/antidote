import random
import threading
import time

import pytest

from antidote import factory, Tagged, world
from antidote.core import DependencyContainer
from antidote.providers.tag import TaggedDependencies


class Service:
    pass


class AnotherService:
    pass


def random_delay(a=0.01, b=None):
    b = b or a
    time.sleep(a + b * random.random())


def delayed_new_class(cls):
    def f() -> cls:
        random_delay()
        return cls()

    return f


@pytest.fixture
def new_world():
    with world.test.new():
        world.singletons.update({Service: Service(), 'parameter': object()})
        yield


def multi_thread_do(target, n_threads=10):
    threads = [threading.Thread(target=target)
               for _ in range(n_threads)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()


@pytest.mark.usefixtures("new_world")
def test_container_instantiation_safety():
    n_threads = 10

    factory(delayed_new_class(Service), singleton=True)
    factory(delayed_new_class(AnotherService), singleton=False)

    singleton_got = []
    non_singleton_got = []

    def worker():
        singleton_got.append(world.get(Service))
        non_singleton_got.append(world.get(AnotherService))

    multi_thread_do(worker, n_threads)

    assert 1 == len(set(singleton_got))
    assert n_threads == len(set(non_singleton_got))


@pytest.mark.usefixtures("new_world")
def test_tagged_dependencies_instantiation_safety():
    n_dependencies = 40

    for i in range(n_dependencies):
        factory(delayed_new_class(type(f'Service{i}', (object,), {})),
                singleton=False,
                tags=['test'])

    tagged: TaggedDependencies = world.get(Tagged('test'))
    dependencies = []

    def worker():
        for i, dep in enumerate(tagged.instances()):
            dependencies.append((i, dep))

    multi_thread_do(worker)

    assert n_dependencies == len(set(dependencies))
    assert set(dependencies) == set(enumerate(tagged.instances()))


def test_world_safety():
    n_threads = 10
    singletons = []

    def worker():
        with world.test.empty():
            r = random.random()
            world.singletons.set("x", r)
            random_delay()
            singletons.append((r, r == world.get("x")))

    multi_thread_do(worker, n_threads)

    assert n_threads == len({r for (r, _) in singletons})
    assert all(equal for (_, equal) in singletons)


def test_sate_init_safety():
    from antidote._internal import state, defaults

    old_new_container = defaults.new_container

    called = 0

    def new_container():
        nonlocal called
        called += 1
        random_delay()
        return old_new_container()

    state.reset()
    defaults.new_container = new_container

    try:
        multi_thread_do(state.init, n_threads=10)
    finally:
        defaults.new_container = old_new_container

    assert state.get_container() is not None
    assert called == 1


def test_state_override_safety():
    from antidote._internal import state

    state.init()
    container = state.get_container()

    def create(c):
        assert c is container
        return DependencyContainer()

    def worker():
        random_delay()
        state.override(create)

    multi_thread_do(worker, n_threads=10)
