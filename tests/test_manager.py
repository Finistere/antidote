import pytest

from blood.manager import ServiceManager
from blood.exceptions import *


def test_inject_with_mapping():
    manager = ServiceManager()
    container = manager.container

    class Service(object):
        pass

    container.register(Service)

    @manager.inject
    def f(x):
        return x

    with pytest.raises(TypeError):
        f()

    @manager.inject(mapping=dict(x=Service))
    def g(x):
        return x

    assert container[Service] is g()

    @manager.inject(mapping=dict(x=Service))
    def h(x, b=1):
        return x

    assert container[Service] is h()


def test_inject_by_name():
    manager = ServiceManager(inject_by_name=False)
    container = manager.container

    _service = object()
    container['service'] = _service

    @manager.inject(inject_by_name=True)
    def f(service):
        return service

    assert _service is f()

    @manager.inject
    def g(service):
        return service

    with pytest.raises(TypeError):
        g()

    @manager.inject(inject_by_name=True)
    def h(service, b=1):
        return service

    assert _service is h()

    manager.inject_by_name = True

    @manager.inject
    def u(service):
        return service

    assert _service is u()

    @manager.inject(inject_by_name=False)
    def v(service):
        return service

    with pytest.raises(TypeError):
        v()


def test_register():
    manager = ServiceManager(auto_wire=True)
    container = manager.container

    @manager.register
    class Service(object):
        pass

    assert isinstance(container[Service], Service)

    s = object()

    with pytest.raises(ValueError):
        manager.register(s)

    manager.register(s, id='service')
    assert s is container['service']

    @manager.register(mapping=dict(service=Service))
    class AnotherService(object):
        def __init__(self, service):
            self.service = service

    assert isinstance(container[AnotherService], AnotherService)
    assert container[Service] is container[AnotherService].service
    # singleton
    assert container[AnotherService] is container[AnotherService]

    @manager.register(inject_by_name=True)
    class YetAnotherService(object):
        def __init__(self, service):
            self.service = service

    assert isinstance(container[YetAnotherService], YetAnotherService)
    assert s is container[YetAnotherService].service
    # singleton
    assert container[YetAnotherService] is container[YetAnotherService]

    @manager.register(singleton=False)
    class SingleUsageService(object):
        pass

    assert isinstance(container[SingleUsageService], SingleUsageService)
    assert container[SingleUsageService] is not container[SingleUsageService]

    @manager.register(auto_wire=False)
    class BrokenService(object):
        def __init__(self, service):
            self.service = service

    with pytest.raises(ServiceInstantiationError):
        _ = container[BrokenService]


