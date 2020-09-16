import pytest

from antidote.core.container import DependencyInstance, RawDependencyContainer, \
    RawDependencyProvider
from antidote.core.exceptions import DuplicateDependencyError
from antidote.exceptions import (DependencyCycleError, DependencyInstantiationError,
                                 DependencyNotFoundError, FrozenContainerError,
                                 FrozenWorldError)
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
    return RawDependencyContainer()


def test_dependency_repr():
    o = object()
    d = DependencyInstance(o, False)

    assert repr(False) in repr(d)
    assert repr(o) in repr(d)


def test_setitem(container: RawDependencyContainer):
    s = object()
    container.update_singletons({'service': s})

    assert s is container.get('service')
    assert s is container.provide('service').instance


def test_update(container: RawDependencyContainer):
    x = object()
    y = object()
    container.update_singletons({'x': x, 'y': y})

    assert container.provide('x').instance is x
    assert container.provide('x').singleton is True
    assert container.get('y') is y


def test_duplicate_singletons(container: RawDependencyContainer):
    x = object()
    container.update_singletons(dict(x=x))

    with pytest.raises(DuplicateDependencyError):
        container.update_singletons(dict(x=object()))

    # did not change singleton
    assert container.get('x') is x


def test_getitem(container: RawDependencyContainer):
    container.register_provider(DummyFactoryProvider)
    container.get(DummyFactoryProvider).data = {
        Service: lambda _: Service(),
        ServiceWithNonMetDependency: lambda _: ServiceWithNonMetDependency(),
    }
    container.register_provider(DummyProvider)
    container.get(DummyProvider).data = {'name': 'Antidote'}

    assert isinstance(container.get(Service), Service)
    assert isinstance(container.provide(Service), DependencyInstance)
    assert 'Antidote' == container.get('name')
    assert 'Antidote' == container.provide('name').instance

    with pytest.raises(DependencyNotFoundError):
        container.get(object)

    with pytest.raises(DependencyInstantiationError):
        container.get(ServiceWithNonMetDependency)


def test_singleton(container: RawDependencyContainer):
    container.register_provider(DummyFactoryProvider)
    container.get(DummyFactoryProvider).data = {
        Service: lambda _: Service(),
        AnotherService: lambda _: AnotherService(),
    }

    service = container.get(Service)
    assert container.get(Service) is service
    assert container.provide(Service).instance is service
    assert container.provide(Service).singleton is True

    container.get(DummyFactoryProvider).singleton = False
    another_service = container.get(AnotherService)
    assert container.get(AnotherService) is not another_service
    assert container.provide(AnotherService).instance is not another_service
    assert container.provide(AnotherService).singleton is False

    assert container.get(Service) == service


def test_dependency_cycle_error(container: RawDependencyContainer):
    container.register_provider(DummyFactoryProvider)
    container.get(DummyFactoryProvider).data = {
        Service: lambda _: Service(container.get(AnotherService)),
        AnotherService: lambda _: AnotherService(container.get(YetAnotherService)),
        YetAnotherService: lambda _: YetAnotherService(container.get(Service)),
    }

    with pytest.raises(DependencyCycleError):
        container.get(Service)

    with pytest.raises(DependencyCycleError):
        container.get(AnotherService)

    with pytest.raises(DependencyCycleError):
        container.get(YetAnotherService)


def test_providers(container: RawDependencyContainer):
    x = object()
    y = object()
    container.register_provider(DummyProvider)
    container.get(DummyProvider).data = dict(x=x)
    container.register_provider(DummyFactoryProvider)
    container.get(DummyFactoryProvider).data = dict(y=lambda c: c.get('y'))

    assert len(container.providers) == 2
    for provider in container.providers:
        if isinstance(provider, DummyProvider):
            assert provider.data == dict(x=x)
        else:
            assert 'y' in provider.data


def test_repr_str(container: RawDependencyContainer):
    container.register_provider(DummyProvider)
    container.get(DummyProvider).data = {'name': 'Antidote'}
    container.update_singletons({'test': 1})

    assert 'test' in repr(container)
    assert repr(container.get(DummyProvider)) in repr(container)
    assert str(container.get(DummyProvider)) in str(container)


def test_invalid_provider(container: RawDependencyContainer):
    with pytest.raises(TypeError):
        container.register_provider(object)

    # Cannot register twice the same kind of provider
    container.register_provider(DummyProvider)
    with pytest.raises(ValueError):
        container.register_provider(DummyProvider)


def test_clone(container: RawDependencyContainer):
    container.register_provider(DummyProvider)
    container.get(DummyProvider).data = {'name': 'Antidote'}
    container.update_singletons({'test': object()})

    cloned = container.clone(keep_singletons=True)
    assert cloned.get('test') is container.get('test')
    assert cloned.get(DummyProvider) is not container.get(DummyProvider)

    cloned.update_singletons({'test2': 2})
    with pytest.raises(DependencyNotFoundError):
        container.get("test2")

    cloned = container.clone(keep_singletons=False)
    with pytest.raises(DependencyNotFoundError):
        cloned.get("test")
    assert cloned.get(DummyProvider) is not container.get(DummyProvider)

    cloned.update_singletons({'test2': 2})
    with pytest.raises(DependencyNotFoundError):
        container.get("test2")


def test_freeze(container: RawDependencyContainer):
    container.register_provider(DummyProvider)
    container.get(DummyProvider).data = {'name': 'Antidote'}
    container.freeze()

    with pytest.raises(FrozenWorldError):
        container.register_provider(DummyFactoryProvider)

    with pytest.raises(FrozenWorldError):
        container.update_singletons({'test': object()})


def test_ensure_not_frozen(container: RawDependencyContainer):
    with container.ensure_not_frozen():
        pass

    container.freeze()

    with pytest.raises(FrozenContainerError):
        with container.ensure_not_frozen():
            pass


def test_singleton_property(container: RawDependencyContainer):
    container.update_singletons({'a': 1})

    assert container.singletons == dict(a=1)
    container.singletons.update({'b': 1})

    with pytest.raises(DependencyNotFoundError):
        container.get('b')


def test_provider_property(container: RawDependencyContainer):
    container.register_provider(DummyProvider)
    assert container.providers == [container.get(DummyProvider)]


def test_providers_must_properly_clone(container: RawDependencyContainer):
    class DummySelf(RawDependencyProvider):
        def clone(self, keep_singletons_cache: bool) -> 'RawDependencyProvider':
            return self

    container.register_provider(DummySelf)

    with pytest.raises(RuntimeError, match="(?i).*provider.*instance.*"):
        container.clone()


def test_providers_must_properly_clone2(container: RawDependencyContainer):
    container.register_provider(DummyProvider)
    p = container.get(DummyProvider)

    class DummyRegistered(RawDependencyProvider):
        def clone(self, keep_singletons_cache: bool) -> 'RawDependencyProvider':
            return p

    container.register_provider(DummyRegistered)
    with pytest.raises(RuntimeError, match="(?i).*provider.*fresh instance.*"):
        container.clone()


def test_clone_providers(container: RawDependencyContainer):
    container.register_provider(DummyProvider)
    data = dict(name='antidote')
    container.get(DummyProvider).data = data

    cloned = container.clone(clone_providers=True)
    assert cloned.get(DummyProvider).data == data

    cloned2 = container.clone(clone_providers=False)
    assert cloned2.get(DummyProvider).data is None
