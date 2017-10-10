import pytest

from dependency_manager import Container
from dependency_manager.exceptions import *


class Service(object):
    pass


class AnotherService(object):
    pass


def test_register():
    container = Container()
    container.register(Service)
    assert isinstance(container[Service], Service)
    # singleton by default
    assert container[Service] is container[Service]


def test_deregister():
    container = Container()
    container.register(Service)
    container.deregister(Service)

    with pytest.raises(UnregisteredServiceError):
        _ = container[Service]

    with pytest.raises(UnregisteredServiceError):
        container.deregister(Service)


def test_cache():
    container = Container()
    container.register(Service)
    x = container[Service]

    assert x is container[Service]


def test_register_factory():
    container = Container()

    class ServiceFactory(object):
        def __call__(self, *args, **kwargs):
            return Service()

    container.register(ServiceFactory(), type=Service)
    assert isinstance(container[Service], Service)


def test_setitem():
    container = Container()

    s = object()
    container['service'] = s

    assert s is container['service']


def test_getitem():
    container = Container()

    with pytest.raises(UnregisteredServiceError):
        _ = container[Service]

    container.register(Service)
    assert isinstance(container[Service], Service)

    class ServiceWithNonMetDependency(object):
        def __init__(self, dependency):
            pass

    container.register(ServiceWithNonMetDependency, singleton=False)

    with pytest.raises(ServiceInstantiationError):
        _ = container[ServiceWithNonMetDependency]

    class SingletonServiceWithNonMetDependency(object):
        def __init__(self, dependency):
            pass

    container.register(SingletonServiceWithNonMetDependency, singleton=True)

    with pytest.raises(ServiceInstantiationError):
        _ = container[SingletonServiceWithNonMetDependency]

    def failing_service_factory():
        raise Exception()

    container.append({
        'test': failing_service_factory
    })

    with pytest.raises(ServiceInstantiationError):
        _ = container['test']


def test_contains():
    container = Container()
    container.register(Service)

    assert Service in container
    assert AnotherService not in container

    container['test'] = object()
    assert 'test' in container


def test_delitem():
    container = Container()
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

    with pytest.raises(UnregisteredServiceError):
        del container['test']


def test_singleton():
    container = Container()

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
    container = Container()
    container.register(Service)

    with pytest.raises(DuplicateServiceError):
        container.register(Service)

    with pytest.raises(DuplicateServiceError):
        container.register(AnotherService, type=Service)


def test_append():
    container = Container()
    container.register(Service)

    another_service = AnotherService()
    y = object()

    container.append({
        Service: another_service,
        'y': y
    })

    assert another_service is not container[Service]
    assert isinstance(container[Service], Service)
    assert y is container['y']


def test_prepend():
    container = Container()
    container.register(Service)

    another_service = AnotherService()
    y = object()

    container.prepend({
        Service: another_service,
        'y': y
    })

    assert another_service is container[Service]
    assert y is container['y']
