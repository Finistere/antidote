import pytest

from dependency_manager import DependencyContainer
from dependency_manager.exceptions import *


class Service(object):
    pass


class AnotherService(object):
    pass


def test_register():
    container = DependencyContainer()
    container.register(Service)
    assert isinstance(container[Service], Service)
    # singleton by default
    assert container[Service] is container[Service]


def test_deregister():
    container = DependencyContainer()
    container.register(Service)
    container.deregister(Service)

    with pytest.raises(UnregisteredDependencyError):
        _ = container[Service]

    with pytest.raises(UnregisteredDependencyError):
        container.deregister(Service)


def test_cache():
    container = DependencyContainer()
    container.register(Service)
    x = container[Service]

    assert x is container[Service]


def test_register_factory():
    container = DependencyContainer()

    class ServiceFactory(object):
        def __call__(self, *args, **kwargs):
            return Service()

    container.register(ServiceFactory(), type=Service)
    assert isinstance(container[Service], Service)


def test_setitem():
    container = DependencyContainer()

    s = object()
    container['service'] = s

    assert s is container['service']


def test_getitem():
    container = DependencyContainer()

    with pytest.raises(UnregisteredDependencyError):
        _ = container[Service]

    container.register(Service)
    assert isinstance(container[Service], Service)

    class ServiceWithNonMetDependency(object):
        def __init__(self, dependency):
            pass

    container.register(ServiceWithNonMetDependency, singleton=False)

    with pytest.raises(DependencyInstantiationError):
        _ = container[ServiceWithNonMetDependency]

    class SingletonServiceWithNonMetDependency(object):
        def __init__(self, dependency):
            pass

    container.register(SingletonServiceWithNonMetDependency, singleton=True)

    with pytest.raises(DependencyInstantiationError):
        _ = container[SingletonServiceWithNonMetDependency]

    def failing_service_factory():
        raise Exception()

    container.extend({
        'test': failing_service_factory
    })

    with pytest.raises(DependencyInstantiationError):
        _ = container['test']


def test_contains():
    container = DependencyContainer()
    container.register(Service)

    assert Service in container
    assert AnotherService not in container

    container['test'] = object()
    assert 'test' in container


def test_delitem():
    container = DependencyContainer()
    container.register(Service)

    # Cannot delete a registered service
    del container[Service]
    assert Service in container

    # But can delete from instantiated / cached services
    x = container[Service]
    del container[Service]
    assert x is not container[Service]

    container['test'] = object()
    del container['test']
    assert 'test' not in container

    with pytest.raises(UnregisteredDependencyError):
        del container['test']


def test_singleton():
    container = DependencyContainer()

    class SingletonService(object):
        pass

    container.register(SingletonService, singleton=True)
    x = container[SingletonService]
    assert isinstance(x, SingletonService)
    assert x is container[SingletonService]

    class SingleUsageService(object):
        pass

    container.register(SingleUsageService, singleton=False)
    x = container[SingleUsageService]
    assert isinstance(x, SingleUsageService)
    assert x is not container[SingleUsageService]


def test_duplicate_error():
    container = DependencyContainer()
    container.register(Service)

    with pytest.raises(DuplicateDependencyError):
        container.register(Service)

    with pytest.raises(DuplicateDependencyError):
        container.register(AnotherService, type=Service)


def test_append():
    container = DependencyContainer()
    container.register(Service)

    another_service = AnotherService()
    y = object()

    container.extend({
        Service: another_service,
        'y': y
    })

    assert another_service is not container[Service]
    assert isinstance(container[Service], Service)
    assert y is container['y']


def test_prepend():
    container = DependencyContainer()
    container.register(Service)

    another_service = AnotherService()
    y = object()

    container.override({
        Service: another_service,
        'y': y
    })

    assert another_service is container[Service]
    assert y is container['y']
