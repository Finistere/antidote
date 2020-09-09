import pytest

from antidote.core import DependencyContainer, DependencyInstance
from antidote.core.exceptions import FrozenWorldError
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
    container.update_singletons({'service': s})

    assert s is container.get('service')
    assert s is container.provide('service').instance


def test_update(container: DependencyContainer):
    container.update_singletons({Service: Service()})

    another_service = AnotherService()
    x = object()

    container.update_singletons({
        Service: another_service,
        'x': x
    })

    assert another_service is container.get(Service)
    assert x is container.provide('x').instance


def test_register_provider(container: DependencyContainer):
    provider = DummyProvider()
    container.register_provider(provider)

    # Can't check directly if the core is the same, as a proxy is used
    assert provider is container.get(DummyProvider)


def test_getitem(container: DependencyContainer):
    container.register_provider(DummyFactoryProvider({
        Service: lambda: Service(),
        ServiceWithNonMetDependency: lambda: ServiceWithNonMetDependency(),
    }))
    container.register_provider(DummyProvider({'name': 'Antidote'}))

    assert isinstance(container.get(Service), Service)
    assert isinstance(container.provide(Service), DependencyInstance)
    assert 'Antidote' == container.get('name')
    assert 'Antidote' == container.provide('name').instance

    with pytest.raises(DependencyNotFoundError):
        container.get(object)

    with pytest.raises(DependencyInstantiationError):
        container.get(ServiceWithNonMetDependency)


def test_singleton(container: DependencyContainer):
    container.register_provider(DummyFactoryProvider({
        Service: lambda: Service(),
        AnotherService: lambda: AnotherService(),
    }))

    service = container.get(Service)
    assert service is container.get(Service)

    container.get(DummyFactoryProvider).singleton = False
    another_service = container.get(AnotherService)
    assert another_service is not container.get(AnotherService)

    assert container.get(Service) == service
    assert container.get(DependencyContainer) == container


def test_dependency_cycle_error(container: DependencyContainer):
    container.register_provider(DummyFactoryProvider({
        Service: lambda: Service(container.get(AnotherService)),
        AnotherService: lambda: AnotherService(container.get(YetAnotherService)),
        YetAnotherService: lambda: YetAnotherService(container.get(Service)),
    }))

    with pytest.raises(DependencyCycleError):
        container.get(Service)

    with pytest.raises(DependencyCycleError):
        container.get(AnotherService)

    with pytest.raises(DependencyCycleError):
        container.get(YetAnotherService)


def test_repr_str(container: DependencyContainer):
    container.register_provider(DummyProvider({'name': 'Antidote'}))
    container.update_singletons({'test': 1})

    assert 'test' in repr(container)
    assert repr(container.get(DummyProvider)) in repr(container)
    assert str(container.get(DummyProvider)) in str(container)


def test_invalid_provider(container: DependencyContainer):
    with pytest.raises(TypeError):
        container.register_provider(object())


def test_clone(container: DependencyContainer):
    container.register_provider(DummyProvider({'name': 'Antidote'}))
    container.update_singletons({'test': object()})

    cloned = container.clone(keep_singletons=True)
    assert cloned.get('test') is container.get('test')
    assert cloned.get(DummyProvider) is not container.get(DummyProvider)
    assert cloned.get(DependencyContainer) is cloned

    cloned.update_singletons({'test2': 2})
    with pytest.raises(DependencyNotFoundError):
        container.get("test2")

    cloned = container.clone(keep_singletons=False)
    with pytest.raises(DependencyNotFoundError):
        cloned.get("test")
    assert cloned.get(DummyProvider) is not container.get(DummyProvider)
    assert cloned.get(DependencyContainer) is cloned

    cloned.update_singletons({'test2': 2})
    with pytest.raises(DependencyNotFoundError):
        container.get("test2")


def test_freeze(container: DependencyContainer):
    container.register_provider(DummyProvider({'name': 'Antidote'}))
    container.freeze()

    with pytest.raises(FrozenWorldError):
        container.register_provider(DummyFactoryProvider())

    with pytest.raises(FrozenWorldError):
        container.update_singletons({'test': object()})

    assert container.get(DummyProvider).frozen is True
