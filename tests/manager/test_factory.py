import pytest

from antidote import DependencyInstantiationError, DependencyManager


def test_factory_function():
    manager = DependencyManager()
    container = manager.container

    class Service:
        pass

    with pytest.raises(ValueError):  # No dependency ID
        @manager.factory
        def faulty_service_provider():
            return Service()

    @manager.factory(dependency_id=Service)
    def service_provider():
        return Service()

    assert isinstance(container[Service], Service)
    # is a singleton
    assert container[Service] is container[Service]

    class AnotherService:
        def __init__(self, service):
            self.service = service

    @manager.factory(arg_map=dict(service=Service),
                     dependency_id=AnotherService)
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

    @manager.factory(use_names=True, dependency_id=YetAnotherService)
    def injected_by_name_provider(test):
        return test

    assert s is container[YetAnotherService]

    with pytest.raises(ValueError):
        manager.factory(1)

    with pytest.raises(ValueError):
        @manager.factory
        class Test:
            pass


def test_factory_not_auto_wire():
    manager = DependencyManager()

    class Service:
        pass

    @manager.factory(auto_wire=False)
    def faulty_service_provider(x) -> Service:
        return Service()

    with pytest.raises(TypeError):
        faulty_service_provider()

    with pytest.raises(DependencyInstantiationError):
        manager.container[Service]

    faulty_service_provider(1)  # does work properly


def test_factory_class_not_auto_wire():
    manager = DependencyManager()

    class Service:
        pass

    with pytest.raises(TypeError):
        @manager.factory(auto_wire=False)
        class FaultyServiceFactory:
            def __init__(self, x):
                pass

            def __call__(self) -> Service:
                return Service()

    @manager.factory(auto_wire=False)
    class FaultyServiceFactory2:
        def __call__(self, x) -> Service:
            return Service()

    with pytest.raises(DependencyInstantiationError):
        manager.container[Service]

    with pytest.raises(TypeError):
        FaultyServiceFactory2()()

    FaultyServiceFactory2()(1)  # does work properly


def test_faulty_factory_class():
    manager = DependencyManager()

    class Service:
        pass

    with pytest.raises(ValueError):
        @manager.factory
        class FaultyServiceFactory:
            def __call__(self):
                return Service()

    with pytest.raises(ValueError):
        @manager.factory(dependency_id=Service)
        class FaultyServiceFactory2:
            pass


def test_factory_class():
    manager = DependencyManager()
    container = manager.container

    class Service:
        pass

    @manager.factory(dependency_id=Service)
    class ServiceProvider:
        def __call__(self):
            return Service()

    assert isinstance(container[Service], Service)
    # is a singleton
    assert container[Service] is container[Service]

    class AnotherService:
        def __init__(self, service):
            self.service = service

    @manager.factory(arg_map=dict(service=Service),
                     dependency_id=AnotherService)
    class AnotherServiceProvider:
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

    class YetAnotherService:
        pass

    @manager.factory(use_names=True, dependency_id=YetAnotherService)
    class YetAnotherServiceProvider:
        def __init__(self, test):
            self.test = test

        def __call__(self, test):
            assert self.test is test
            return test

    assert container['test'] is container[YetAnotherService]

    class OtherService:
        pass

    @manager.factory(use_names=True,
                     arg_map=dict(service=Service),
                     auto_wire=('__init__',),
                     dependency_id=OtherService)
    class OtherServiceProvider:
        def __init__(self, test, service):
            self.test = test
            self.service = service

        def __call__(self):
            return self.test, self.service

    output = container[OtherService]
    assert output[0] is container['test']
    assert isinstance(output[1], Service)
