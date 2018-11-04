import pytest

from antidote import (DependencyManager, DependencyNotFoundError,
                      DependencyNotProvidableError, Instance)
from antidote.providers import FactoryProvider, ParameterProvider


def test_provider():
    manager = DependencyManager()
    container = manager.container

    container['service'] = object()

    @manager.provider(use_names=True)
    class DummyProvider:
        def __init__(self, service=None):
            self.service = service

        def __antidote_provide__(self, dependency):
            if dependency.id == 'test':
                return Instance(dependency.id)
            else:
                raise DependencyNotProvidableError(dependency)

    assert isinstance(container.providers[DummyProvider], DummyProvider)
    assert container.providers[DummyProvider].service is container['service']
    assert 'test' == container['test']

    with pytest.raises(DependencyNotFoundError):
        container['test2']

    with pytest.raises(ValueError):
        manager.provider(object())

    with pytest.raises(ValueError):
        @manager.provider
        class MissingAntidoteProvideMethod:
            pass

    with pytest.raises(TypeError):
        @manager.provider(auto_wire=False)
        class MissingDependencyProvider:
            def __init__(self, service):
                self.service = service

            def __antidote_provide__(self, dependency):
                return Instance(dependency.id)


def test_providers():
    manager = DependencyManager()

    assert 2 == len(manager.providers)
    assert FactoryProvider in manager.providers
    assert ParameterProvider in manager.providers

    @manager.provider
    class DummyProvider:
        def __antidote_provide__(self, dependency):
            return Instance(1)

    assert DummyProvider in manager.providers
