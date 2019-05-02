import pytest

from antidote import new_container, provider
from antidote.core import DependencyInstance, DependencyProvider
from antidote.providers import (IndirectProvider, LazyCallProvider, FactoryProvider,
                                TagProvider)


@pytest.fixture()
def container():
    return new_container()


def test_simple(container):
    container.update_singletons({'service': object()})

    @provider(container=container, wire_super=True)
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
    assert 4 == len(container.providers)
    assert FactoryProvider in container.providers
    assert TagProvider in container.providers
    assert LazyCallProvider in container.providers
    assert IndirectProvider in container.providers

    @provider(container=container, wire_super=True)
    class DummyProvider(DependencyProvider):
        def provide(self, dependency):
            return DependencyInstance(1)

    assert DummyProvider in container.providers
