from typing import Any

import pytest

from antidote.core import DependencyContainer, DependencyInstance, DependencyProvider
from antidote.exceptions import (DependencyCycleError, DependencyInstantiationError,
                                 DependencyNotFoundError)
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
    d = DependencyInstance(o, False)

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

    container.update_singletons({
        Service: another_service,
        'x': x
    })

    assert another_service is container[Service]
    assert x is container['x']


def test_register_provider(container: DependencyContainer):
    provider = DummyProvider()
    container.register_provider(provider)

    # Can't check directly if the core is the same, as a proxy is used
    assert provider is container.providers[DummyProvider]


def test_getitem(container: DependencyContainer):
    container.register_provider(DummyFactoryProvider({
        Service: lambda: Service(),
        ServiceWithNonMetDependency: lambda: ServiceWithNonMetDependency(),
    }))
    container.register_provider(DummyProvider({'name': 'Antidote'}))

    with pytest.raises(DependencyNotFoundError):
        container[object]

    with pytest.raises(DependencyInstantiationError):
        container[ServiceWithNonMetDependency]

    assert isinstance(container[Service], Service)
    assert isinstance(container.provide(Service), Service)
    assert 'Antidote' == container['name']
    assert 'Antidote' == container.provide('name')


def test_singleton(container: DependencyContainer):
    container.register_provider(DummyFactoryProvider({
        Service: lambda: Service(),
        AnotherService: lambda: AnotherService(),
    }))

    service = container[Service]
    assert service is container[Service]

    container.providers[DummyFactoryProvider].singleton = False
    another_service = container[AnotherService]
    assert another_service is not container[AnotherService]

    assert {Service: service, DependencyContainer: container} == container.singletons


def test_dependency_cycle_error(container: DependencyContainer):
    container.register_provider(DummyFactoryProvider({
        Service: lambda: Service(container[AnotherService]),
        AnotherService: lambda: AnotherService(container[YetAnotherService]),
        YetAnotherService: lambda: YetAnotherService(container[Service]),
    }))

    with pytest.raises(DependencyCycleError):
        container[Service]

    with pytest.raises(DependencyCycleError):
        container[AnotherService]

    with pytest.raises(DependencyCycleError):
        container[YetAnotherService]


def test_repr_str(container: DependencyContainer):
    container.register_provider(DummyProvider({'name': 'Antidote'}))
    container['test'] = 1

    assert 'test' in repr(container)
    assert repr(container.providers[DummyProvider]) in repr(container)
    assert str(container.providers[DummyProvider]) in str(container)


def test_invalid_provider(container: DependencyContainer):
    with pytest.raises(ValueError):
        container.register_provider(object())


def test_bound_dependency_types():
    class CustomDependency:
        pass

    class DummyProvider1(DependencyProvider):
        bound_dependency_types = (CustomDependency,)

        def provide(self, dependency: Any) -> DependencyInstance:
            return DependencyInstance(self)

    class DummyProvider2(DependencyProvider):
        def provide(self, dependency: Any) -> DependencyInstance:
            raise Exception()

    container = DependencyContainer()
    container.register_provider(DummyProvider2(container))
    container.register_provider(DummyProvider1(container))
    assert isinstance(container[CustomDependency()], DummyProvider1)

    container = DependencyContainer()
    container.register_provider(DummyProvider1(container))
    container.register_provider(DummyProvider2(container))
    assert isinstance(container[CustomDependency()], DummyProvider1)


def test_bound_dependency_types_conflict():
    class CustomDependency:
        pass

    class DummyProvider1(DependencyProvider):
        bound_dependency_types = (CustomDependency,)

        def provide(self, dependency: Any) -> DependencyInstance:
            return DependencyInstance(self)

    class DummyProvider2(DependencyProvider):
        bound_dependency_types = (CustomDependency,)

        def provide(self, dependency: Any) -> DependencyInstance:
            return DependencyInstance(self)

    container = DependencyContainer()
    container.register_provider(DummyProvider1(container))

    with pytest.raises(RuntimeError):
        container.register_provider(DummyProvider2(container))
