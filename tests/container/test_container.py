import pytest

from antidote.container import Dependency, DependencyContainer, Prepare
from antidote.exceptions import (
    DependencyNotFoundError, DependencyNotProvidableError,
    DependencyCycleError, DependencyInstantiationError
)


class DummyProvider(object):
    singleton = True

    def __init__(self, data=None):
        self.data = data or dict()

    def __setitem__(self, key, value):
        self.data[key] = value

    def __antidote_provide__(self, dependency_id, *args, **kwargs):
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

    def __antidote_provide__(self, dependency_id, *args, **kwargs):
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


def test_dependency_repr():
    o = object()
    d = Dependency(o, False)

    assert repr(False) in repr(d)
    assert repr(o) in repr(d)


def test_setitem():
    container = DependencyContainer()

    s = object()
    container['service'] = s

    assert s is container['service']
    assert repr(s) in repr(container)


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


def test_getitem_and_provide():
    container = DependencyContainer()
    container.providers[DummyFactoryProvider] = DummyFactoryProvider({
        Service: lambda: Service(),
        ServiceWithNonMetDependency: lambda: ServiceWithNonMetDependency(),
    })
    container.providers[DummyProvider] = DummyProvider({'name': 'Antidote'})

    for get in (container.__getitem__, container.provide):
        with pytest.raises(KeyError):
            get(object)

        with pytest.raises(DependencyNotFoundError):
            get(object)

        with pytest.raises(DependencyInstantiationError):
            get(ServiceWithNonMetDependency)

    assert isinstance(container[Service], Service)
    assert isinstance(container[Prepare(Service)], Service)
    assert isinstance(container.provide(Service), Service)
    assert 'Antidote' == container['name']
    assert 'Antidote' == container[Prepare('name')]
    assert 'Antidote' == container.provide('name')


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


def test_repr():
    container = DependencyContainer()
    container.providers[DummyProvider] = DummyProvider({'name': 'Antidote'})
    container['test'] = 1

    assert 'test' in repr(container)
    assert repr(container.providers[DummyProvider]) in repr(container)
