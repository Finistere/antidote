import pytest

from antidote.container import Dependency, DependencyContainer
from antidote.exceptions import *


class DummyProvider(object):
    singleton = True

    def __init__(self, data=None):
        self.data = data or dict()

    def __setitem__(self, key, value):
        self.data[key] = value

    def __antidote_provide__(self, dependency_id):
        try:
            return Dependency(self.data[dependency_id],
                              singleton=self.singleton)
        except KeyError:
            raise DependencyNotProvidableError(dependency_id)


class DummyFactoryProvider(object):
    create_singleton = True

    def __init__(self, data=None):
        self.data = data or dict()

    def __setitem__(self, key, value):
        self.data[key] = value

    def __antidote_provide__(self, dependency_id):
        try:
            return Dependency(self.data[dependency_id](),
                              singleton=self.create_singleton)
        except KeyError:
            raise DependencyNotProvidableError(dependency_id)


class Service(object):
    def __init__(self, *args):
        pass


class AnotherService(object):
    def __init__(self, *args):
        pass


class YetAnotherService(object):
    def __init__(self, *args):
        pass


class ServiceWithNonMetDependency(object):
    def __init__(self, dependency):
        pass


def test_setitem():
    container = DependencyContainer()

    s = object()
    container['service'] = s

    assert s is container['service']


def test_update():
    container = DependencyContainer()
    container[Service] = Service()

    another_service = AnotherService()
    x = object()

    container.update({
        Service: another_service,
        'x': x
    })

    assert another_service is container[Service]
    assert x is container['x']


def test_extend():
    container = DependencyContainer()

    provider = DummyProvider()
    container.providers[DummyProvider] = provider

    # Can't check directly if the container is the same, as a proxy is used
    assert provider is container.providers[DummyProvider]


def test_getitem():
    container = DependencyContainer()
    container.providers[DummyFactoryProvider] = DummyFactoryProvider({
        Service: lambda: Service(),
        ServiceWithNonMetDependency: lambda: ServiceWithNonMetDependency(),
    })
    container.providers[DummyProvider] = DummyProvider({'name': 'Antidote'})

    with pytest.raises(KeyError):
        container[object]

    with pytest.raises(DependencyNotFoundError):
        container[object]

    assert isinstance(container[Service], Service)
    assert 'Antidote' == container['name']

    with pytest.raises(DependencyInstantiationError):
        container[ServiceWithNonMetDependency]


def test_singleton():
    container = DependencyContainer()
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


def test_cycle_error():
    container = DependencyContainer()
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
