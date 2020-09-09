import pytest

from antidote import provider, world
from antidote.core import DependencyInstance, DependencyProvider


@pytest.fixture(autouse=True)
def test_world():
    with world.test.new():
        yield


def test_simple():
    world.singletons.update({'service': object()})

    @provider(wire_super=True)
    class DummyProvider(DependencyProvider):
        def provide(self, dependency, container):
            if dependency == 'test':
                return DependencyInstance(dependency)

    assert isinstance(world.get(DummyProvider), DummyProvider)
    assert 'test' == world.get('test')


@pytest.mark.parametrize('cls', [1, type('MissingCall', tuple(), {})])
def test_invalid_provider(cls):
    with pytest.raises(TypeError):
        provider(cls)
