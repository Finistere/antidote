import pytest

from blood.container import ServiceManager
from blood.exceptions import *


def test_register():
    manager = ServiceManager()

    @manager.register
    class Service(object):
        pass

    assert isinstance(manager.container[Service], Service)

    s = object()

    with pytest.raises(ValueError):
        manager.register(s)

    manager.register(s, id='service')
    assert s == manager.container['service']

    @manager.register(mapping=dict(service=Service))
    class AnotherService(object):
        def __init__(self, service):
            self.service = service

    assert isinstance(manager.container[AnotherService].service, Service)


def test_inject():
    manager = ServiceManager()

    @manager.register
    class Service(object):
        pass

    @manager.inject(mapping=dict(x=Service))
    def f3(x):
        return x

    assert isinstance(f3(), Service)

    @manager.inject(mapping=dict(x=Service))
    def f4(x, b=1):
        return x

    assert isinstance(f4(), Service)


def test_auto_wire():
    manager = ServiceManager()

    @manager.register(id='s1')
    class Service(object):
        pass

    @manager.register(id='s2', mapping=dict(s1=Service))
    class AnotherService(object):
        def __init__(self, s1):
            self.s1 = s1

    @manager.register(id='s3', auto_wire=False)
    class S3(AnotherService):
        def __init__(self, s2, **kwargs):
            super(S3, self).__init__(**kwargs)
            self.s2 = s2

    assert isinstance(manager.container['s2'].s1, Service)

    with pytest.raises(ServiceInstantiationError):
        _ = manager.container['s3']


def test_no_duplicates():
    manager = ServiceManager()

    @manager.register(id='test')
    class Service(object):
        pass

    class AnotherService(object):
        pass

    with pytest.raises(DuplicateServiceError):
        manager.register(Service)

    with pytest.raises(DuplicateServiceError):
        manager.register(AnotherService, id='test')


def test_override():
    manager = ServiceManager()

    @manager.register(id='test')
    class Service(object):
        pass

    assert isinstance(manager.container['test'], Service)

    service = object()
    manager.container['test'] = service
    assert service == manager.container['test']


def test_service_instantiation_error():
    manager = ServiceManager()

    @manager.register
    class Service(object):
        def __init__(self, x):
            pass

    with pytest.raises(ServiceInstantiationError):
        _ = manager.container[Service]


def test_service_with_default_values():
    manager = ServiceManager()

    @manager.register
    class Service(object):
        def __init__(self, x=1):
            pass

    assert isinstance(manager.container[Service], Service)

