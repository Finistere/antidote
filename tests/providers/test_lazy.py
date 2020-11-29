import pytest

from antidote import world
from antidote._extension.providers.lazy import FastLazyConst, Lazy, LazyProvider
from antidote.core import Container, DependencyInstance


@pytest.fixture()
def lazy_provider():
    with world.test.empty():
        world.provider(LazyProvider)
        yield world.get(LazyProvider)


class Dummy(Lazy):
    def __init__(self, value, singleton=False):
        self.value = value
        self.singleton = singleton

    def lazy_get(self, container: Container) -> DependencyInstance:
        return DependencyInstance(container.get(self.value), self.singleton)


def test_lazy():
    with world.test.empty():
        x = object()
        world.singletons.add(x, object())
        lazy_provider = LazyProvider()

        assert world.test.maybe_provide_from(lazy_provider,
                                             Dummy(x)).value is world.get(x)
        for s in [True, False]:
            assert world.test.maybe_provide_from(lazy_provider,
                                                 Dummy(x, singleton=s)).singleton is s


def test_exists():
    lazy = LazyProvider()
    assert not lazy.exists(object())
    assert lazy.exists(Dummy('x'))


def test_fast_lazy_method(lazy_provider: LazyProvider):
    class A:
        def method(self, value):
            return self, value

    world.singletons.add(A, A())
    x = object()
    (owner, value) = world.get(FastLazyConst(A, 'method', x))
    assert owner is world.get(A)
    assert value is x


def test_copy(lazy_provider: LazyProvider):
    assert isinstance(lazy_provider.clone(True), LazyProvider)
    assert isinstance(lazy_provider.clone(False), LazyProvider)
