import random
import threading
import time

from antidote import factory, Tag, TaggedDependencies, world
from antidote.core import DependencyContainer


class A:
    pass


class B:
    pass


def random_delay(a=0.01, b=None):
    b = b or a
    time.sleep(a + b * random.random())


def delayed_new_class(cls):
    def f() -> cls:
        random_delay()
        return cls()

    return f


def multi_thread_do(target, n_threads=10):
    threads = [threading.Thread(target=target)
               for _ in range(n_threads)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()


def test_container_instantiation_safety():
    with world.test.new():
        n_threads = 10

        build_a = factory(delayed_new_class(A), singleton=True, auto_wire=False)
        build_b = factory(delayed_new_class(B), singleton=False, auto_wire=False)

        singleton_got = []
        non_singleton_got = []

        def worker():
            singleton_got.append(world.get(A @ build_a))
            non_singleton_got.append(world.get(B @ build_b))

        multi_thread_do(worker, n_threads)

        assert len(set(singleton_got)) == 1
        assert len(set(non_singleton_got)) == n_threads


def test_tagged_dependencies_instantiation_safety():
    with world.test.new():
        tag = Tag()
        n_dependencies = 40

        for i in range(n_dependencies):
            factory(delayed_new_class(type(f'Service{i}', (object,), {})),
                    singleton=False,
                    tags=[tag])

        tagged: TaggedDependencies = world.get(tag)
        dependencies = []

        def worker():
            for i, dep in enumerate(tagged.values()):
                dependencies.append((i, dep))

        multi_thread_do(worker)

        assert len(set(dependencies)) == n_dependencies
        assert set(enumerate(tagged.values())) == set(dependencies)


# Be sure not have used a fixture to create a new test world as it will
# interfere with this test.
def test_world_safety():
    n_threads = 10
    singletons = []

    def worker():
        with world.test.empty():
            tid = (threading.get_ident(), random.random())
            world.singletons.set("x", tid)
            random_delay()
            singletons.append((tid, tid == world.get("x")))

    multi_thread_do(worker, n_threads)

    assert n_threads == len({tid for (tid, _) in singletons})
    assert all(equal for (_, equal) in singletons)


def test_sate_init_safety():
    from antidote._internal import state
    from antidote._internal.utils import world as world_utils

    old_new_container = world_utils.new_container

    called = 0

    def new_container():
        nonlocal called
        called += 1
        random_delay()
        return old_new_container()

    state.reset()
    world_utils.new_container = new_container

    try:
        multi_thread_do(state.init, n_threads=10)
    finally:
        world_utils.new_container = old_new_container

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
