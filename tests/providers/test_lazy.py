import pytest

from antidote import world
from antidote.core import DependencyContainer, DependencyInstance
from antidote.providers.lazy import FastLazyMethod, Lazy, LazyProvider


@pytest.fixture
def lazy_provider():
    with world.test.empty():
        world.provider(LazyProvider)
        yield world.get(LazyProvider)


def test_lazy(lazy_provider: LazyProvider):
    x = object()
    world.singletons.set(x, object())

    class Dummy(Lazy):
        def __init__(self, value, singleton=False):
            self.value = value
            self.singleton = singleton

        def lazy_get(self, container: DependencyContainer) -> DependencyInstance:
            return DependencyInstance(container.get(self.value), self.singleton)

    assert lazy_provider.test_provide(Dummy(x)).instance is world.get(x)
    for s in [True, False]:
        assert lazy_provider.test_provide(Dummy(x, singleton=s)).singleton is s


def test_fast_lazy_method(lazy_provider: LazyProvider):
    class A:
        def method(self, value):
            return self, value

    world.singletons.set(A, A())
    x = object()
    (owner, value) = world.get(FastLazyMethod(A, 'method', x))
    assert owner is world.get(A)
    assert value is x


def test_copy(lazy_provider: LazyProvider):
    assert isinstance(lazy_provider.clone(keep_singletons_cache=True), LazyProvider)
    assert isinstance(lazy_provider.clone(keep_singletons_cache=False), LazyProvider)
