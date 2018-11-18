import pytest

from antidote import (Dependency, DependencyContainer, DependencyCycleError,
                      DependencyInstantiationError, DependencyNotFoundError,
                      Instance)
from .utils import DummyFactoryProvider, DummyProvider


class Service:
    def __init__(self, *args):
        pass


class AnotherService:
    def __init__(self, *args):
        pass


class YetAnotherService:
    def __init__(self, *args):
        pass


class ServiceWithNonMetDependency:
    def __init__(self, dependency):
        pass


@pytest.fixture()
def container():
    return DependencyContainer()


def test_dependency_repr():
    o = object()
    d = Instance(o, False)

    assert repr(False) in repr(d)
    assert repr(o) in repr(d)


def test_setitem(container: DependencyContainer):
    s = object()
    container['service'] = s

    assert s is container['service']
    assert repr(s) in repr(container)


def test_update(container: DependencyContainer):
    container[Service] = Service()

    another_service = AnotherService()
    x = object()

    container.update({
        Service: another_service,
        'x': x
    })

    assert another_service is container[Service]
    assert x is container['x']


def test_extend(container: DependencyContainer):
    provider = DummyProvider()
    container.providers[DummyProvider] = provider

    # Can't check directly if the container is the same, as a proxy is used
    assert provider is container.providers[DummyProvider]


def test_getitem(container: DependencyContainer):
    container.providers[DummyFactoryProvider] = DummyFactoryProvider({
        Service: lambda: Service(),
        ServiceWithNonMetDependency: lambda: ServiceWithNonMetDependency(),
    })
    container.providers[DummyProvider] = DummyProvider({'name': 'Antidote'})

    with pytest.raises(DependencyNotFoundError):
        container[object]

    with pytest.raises(DependencyInstantiationError):
        container[ServiceWithNonMetDependency]

    assert isinstance(container[Service], Service)
    assert isinstance(container[Dependency(Service)], Service)
    assert 'Antidote' == container['name']
    assert 'Antidote' == container[Dependency('name')]


def test_singleton(container: DependencyContainer):
    container.providers[DummyFactoryProvider] = DummyFactoryProvider({
        Service: lambda: Service(),
        AnotherService: lambda: AnotherService(),
    })

    service = container[Service]
    container.providers[DummyFactoryProvider][Service] = lambda: object()
    assert service is container[Service]

    container.providers[DummyFactoryProvider].create_singleton = False
    another_service = container[AnotherService]
    assert another_service is not container[AnotherService]


def test_cycle_error(container: DependencyContainer):
    container.providers[DummyFactoryProvider] = DummyFactoryProvider({
        Service: lambda: Service(container[AnotherService]),
        AnotherService: lambda: AnotherService(container[YetAnotherService]),
        YetAnotherService: lambda: YetAnotherService(container[Service]),
    })

    with pytest.raises(DependencyCycleError):
        container[Service]

    with pytest.raises(DependencyCycleError):
        container[AnotherService]

    with pytest.raises(DependencyCycleError):
        container[YetAnotherService]


def test_repr_str(container: DependencyContainer):
    container.providers[DummyProvider] = DummyProvider({'name': 'Antidote'})
    container['test'] = 1

    assert 'test' in repr(container)
    assert repr(container.providers[DummyProvider]) in repr(container)
    assert str(container.providers[DummyProvider]) in str(container)
