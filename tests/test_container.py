import pytest

from blood.container import ServiceContainer
from blood.exceptions import *


def test_register():
    container = ServiceContainer()

    class Service(object):
        pass

    container.register(Service)
    assert isinstance(container[Service], Service)


def test_register_factory():
    container = ServiceContainer()

    class Service(object):
        pass

    class ServiceFactory(object):
        def __call__(self, *args, **kwargs):
            return Service()

    container.register(ServiceFactory(), type=Service)
    assert isinstance(container[Service], Service)


def test_register_with_id():
    container = ServiceContainer()

    class Service(object):
        pass

    container.register(Service)

    class NewService(object):
        pass

    # id overrides anything
    container.register(NewService, id=Service)
    assert isinstance(container[NewService], NewService)
    assert isinstance(container[Service], NewService)


def test_setitem():
    container = ServiceContainer()

    s = object()
    container['service'] = s

    assert s == container['service']


def test_getitem():
    container = ServiceContainer()

    class Service(object):
        pass

    with pytest.raises(UndefinedServiceError):
        _ = container[Service]

    container.register(Service)
    assert isinstance(container[Service], Service)

    class ServiceWithNonMetDependency(object):
        def __init__(self, dependency):
            pass

    container.register(ServiceWithNonMetDependency)

    with pytest.raises(ServiceInstantiationError):
        _ = container[ServiceWithNonMetDependency]


def test_singleton():
    container = ServiceContainer()

    class SingletonService(object):
        pass

    container.register(SingletonService, singleton=True)
    assert isinstance(container[SingletonService], SingletonService)


def test_duplicates():
    container = ServiceContainer()

    class Service(object):
        pass

    container.register(Service, id='service')

    class AnotherService(object):
        pass

    with pytest.raises(DuplicateServiceError):
        container.register(AnotherService, type=Service)

    container.register(AnotherService, type=Service, force=True)
    assert isinstance(container[Service], AnotherService)

    with pytest.raises(DuplicateServiceError):
        container.register(AnotherService, id='service')

    container.register(AnotherService, id='service', force=True)
    assert isinstance(container['service'], AnotherService)

    class YetAnotherService(object):
        pass

    with pytest.raises(DuplicateServiceError):
        container.register(YetAnotherService, type=Service, id='service')

    container.register(YetAnotherService, type=Service, id='service',
                       force=True)
    assert isinstance(container[Service], YetAnotherService)
    assert isinstance(container['service'], YetAnotherService)


def test_extend():
    base_container = ServiceContainer()
    container1 = ServiceContainer()
    container2 = ServiceContainer()

    class Service(object):
        pass

    class OtherService(object):
        pass

    class NewService(Service):
        pass

    base_container.register(Service)
    base_container.register(OtherService)

    container1.register(NewService, type=Service)
    container2.register(NewService, type=Service)

    # extend current container with some defaults
    container1.extend(base_container)
    assert isinstance(container1[Service], NewService)
    assert isinstance(container1[OtherService], OtherService)

    # override any service definition from current container
    container2.extend(base_container, override=True)
    assert isinstance(container2[Service], Service)
    assert isinstance(container2[OtherService], OtherService)