import pytest

from dependency_manager.manager import DependencyManager
from dependency_manager.exceptions import *


def test_inject_with_mapping():
    manager = DependencyManager()
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


def test_use_arg_name():
    manager = DependencyManager(use_arg_name=False)
    container = manager.container

    _service = object()
    container['service'] = _service

    @manager.inject(use_arg_name=True)
    def f(service):
        return service

    assert _service is f()

    @manager.inject
    def g(service):
        return service

    with pytest.raises(TypeError):
        g()

    @manager.inject(use_arg_name=True)
    def h(service, b=1):
        return service

    assert _service is h()

    manager.use_arg_name = True

    @manager.inject
    def u(service):
        return service

    assert _service is u()

    @manager.inject(use_arg_name=False)
    def v(service):
        return service

    with pytest.raises(TypeError):
        v()


def test_register():
    manager = DependencyManager(auto_wire=True)
    container = manager.container

    @manager.register
    class Service(object):
        pass

    assert isinstance(container[Service], Service)

    class ExternalService(object):
        pass

    s = ExternalService()
    manager.register(s)

    assert s is container[ExternalService]

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

    @manager.register(use_arg_name=True)
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

    with pytest.raises(DependencyInstantiationError):
        _ = container[BrokenService]

    @manager.register(auto_wire=('__init__', 'method'),
                      mapping=dict(service=Service,
                                   x=SingleUsageService,
                                   yet=YetAnotherService))
    class ComplexWiringService(object):
        def __init__(self, service):
            self.service = service

        def method(self, x, yet):
            return x, yet

    assert isinstance(container[ComplexWiringService], ComplexWiringService)
    assert container[Service] is container[ComplexWiringService].service
    output = container[ComplexWiringService].method()

    assert isinstance(output[0], SingleUsageService)
    assert output[1] is container[YetAnotherService]


def test_provider_function():
    manager = DependencyManager()
    container = manager.container

    class Service(object):
        pass

    with pytest.raises(ValueError):
        @manager.provider
        def faulty_service_provider():
            return Service()

    @manager.provider(returns=Service)
    def service_provider():
        return Service()

    assert isinstance(container[Service], Service)
    # is a singleton
    assert container[Service] is container[Service]

    class AnotherService(object):
        def __init__(self, service):
            self.service = service

    @manager.provider(mapping=dict(service=Service), returns=AnotherService)
    def another_service_provider(service):
        return AnotherService(service)

    assert isinstance(container[AnotherService], AnotherService)
    # is a singleton
    assert container[AnotherService] is container[AnotherService]
    assert isinstance(container[AnotherService].service, Service)

    s = object()
    container['test'] = s

    class YetAnotherService:
        pass

    @manager.provider(use_arg_name=True, returns=YetAnotherService)
    def injected_by_name_provider(test):
        return test

    assert s is container[YetAnotherService]


def test_provider_class():
    manager = DependencyManager()
    container = manager.container

    class Service(object):
        pass

    with pytest.raises(ValueError):
        @manager.provider
        class FaultyServiceProvider(object):
            def __call__(self):
                return Service()

    @manager.provider(returns=Service)
    class ServiceProvider(object):
        def __call__(self):
            return Service()

    assert isinstance(container[Service], Service)
    # is a singleton
    assert container[Service] is container[Service]

    class AnotherService(object):
        def __init__(self, service):
            self.service = service

    @manager.provider(mapping=dict(service=Service), returns=AnotherService)
    class AnotherServiceProvider(object):
        def __init__(self, service):
            self.service = service
            assert isinstance(service, Service)

        def __call__(self, service):
            assert self.service is service
            return AnotherService(service)

    assert isinstance(container[AnotherService], AnotherService)
    # is a singleton
    assert container[AnotherService] is container[AnotherService]
    assert isinstance(container[AnotherService].service, Service)

    container['test'] = object()

    class YetAnotherService(object):
        pass

    @manager.provider(use_arg_name=True, returns=YetAnotherService)
    class YetAnotherServiceProvider(object):
        def __init__(self, test):
            self.test = test

        def __call__(self, test):
            assert self.test is test
            return test

    assert container['test'] is container[YetAnotherService]

    class OtherService(object):
        pass

    @manager.provider(use_arg_name=True,
                      mapping=dict(service=Service),
                      auto_wire=('__init__',),
                      returns=OtherService)
    class OtherServiceProvider(object):
        def __init__(self, test, service):
            self.test = test
            self.service = service

        def __call__(self):
            return self.test, self.service

    output = container[OtherService]
    assert output[0] is container['test']
    assert isinstance(output[1], Service)
