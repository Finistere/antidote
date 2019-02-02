import pytest

from antidote import new_container, provider
from antidote.core import DependencyInstance, DependencyProvider
from antidote.providers import ServiceProvider, ResourceProvider, TagProvider


@pytest.fixture()
def container():
    return new_container()


def test_simple(container):
    container.update_singletons({'service': object()})

    @provider(container=container, use_mro=True)
    class DummyProvider(DependencyProvider):
        def provide(self, dependency):
            if dependency == 'test':
                return DependencyInstance(dependency)

    assert isinstance(container.providers[DummyProvider], DummyProvider)
    assert 'test' == container.get('test')


@pytest.mark.parametrize('cls', [1, type('MissingCall', tuple(), {})])
def test_invalid_provider(cls):
    with pytest.raises(TypeError):
        provider(cls)


def test_providers(container):
    assert 3 == len(container.providers)
    assert ServiceProvider in container.providers
    assert ResourceProvider in container.providers
    assert TagProvider in container.providers

    @provider(container=container, use_mro=True)
    class DummyProvider(DependencyProvider):
        def provide(self, dependency):
            return DependencyInstance(1)

    assert DummyProvider in container.providers
