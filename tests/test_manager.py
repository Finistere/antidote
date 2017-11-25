import pytest

from antidote.manager import DependencyManager
from antidote import DependencyInstantiationError


def test_inject_static():
    manager = DependencyManager()
    container = manager.container

    class Service(object):
        pass

    container.register(Service)

    @manager.inject(bind=True)
    def f(x):
        return x

    with pytest.raises(TypeError):
        f()

    @manager.inject(mapping=dict(x=Service), bind=True)
    def g(x):
        return x

    assert container[Service] is g()

    # arguments are bound, so one should not be able to pass injected
    # argument.
    with pytest.raises(TypeError):
        g(1)

    container['service'] = container[Service]

    @manager.inject(use_arg_name=True, bind=True)
    def h(service, b=1):
        return service

    assert container[Service] is h()


def test_inject_with_mapping():
    manager = DependencyManager()
    container = manager.container

    class Service(object):
        pass

    container.register(Service)

    class AnotherService(object):
        pass

    container.register(AnotherService)

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

    manager.mapping = dict(x=Service, y=Service)

    @manager.inject
    def u(x):
        return x

    assert container[Service] is u()

    @manager.inject(mapping=dict(y=AnotherService))
    def v(x, y):
        return x, y

    assert container[Service] is v()[0]
    assert container[AnotherService] is v()[1]


def test_wire():
    manager = DependencyManager()
    container = manager.container

    class Service(object):
        pass

    class AnotherService(object):
        pass

    container.register(Service)
    container.register(AnotherService)

    @manager.wire(mapping=dict(service=Service,
                               another_service=AnotherService))
    class Something(object):
        def f(self, service):
            return service

        def g(self, another_service):
            return another_service

        def h(self, service, another_service):
            return service, another_service

        def u(self):
            pass

        def v(self, nothing):
            return nothing

    something = Something()
    assert container[Service] is something.f()
    assert container[AnotherService] is something.g()

    s1, s2 = something.h()
    assert container[Service] is s1
    assert container[AnotherService] is s2

    something.u()

    with pytest.raises(TypeError):
        something.v()


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

    @manager.service
    class Service(object):
        pass

    assert isinstance(container[Service], Service)

    @manager.service(mapping=dict(service=Service))
    class AnotherService(object):
        def __init__(self, service):
            self.service = service

    assert isinstance(container[AnotherService], AnotherService)
    assert container[Service] is container[AnotherService].service
    # singleton
    assert container[AnotherService] is container[AnotherService]

    container['service'] = object()

    @manager.service(use_arg_name=True)
    class YetAnotherService(object):
        def __init__(self, service):
            self.service = service

    assert isinstance(container[YetAnotherService], YetAnotherService)
    assert container['service'] is container[YetAnotherService].service
    # singleton
    assert container[YetAnotherService] is container[YetAnotherService]

    @manager.service(singleton=False)
    class SingleUsageService(object):
        pass

    assert isinstance(container[SingleUsageService], SingleUsageService)
    assert container[SingleUsageService] is not container[SingleUsageService]

    @manager.service(auto_wire=False)
    class BrokenService(object):
        def __init__(self, service):
            self.service = service

    with pytest.raises(DependencyInstantiationError):
        _ = container[BrokenService]

    @manager.service(auto_wire=('__init__', 'method'),
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


def test_register_non_class():
    manager = DependencyManager()

    with pytest.raises(ValueError):
        manager.service(object())

    def f():
        pass

    with pytest.raises(ValueError):
        manager.service(f)


def test_factory_function():
    manager = DependencyManager()
    container = manager.container

    class Service(object):
        pass

    with pytest.raises(ValueError):
        @manager.factory
        def faulty_service_provider():
            return Service()

    @manager.factory(id=Service)
    def service_provider():
        return Service()

    assert isinstance(container[Service], Service)
    # is a singleton
    assert container[Service] is container[Service]

    class AnotherService(object):
        def __init__(self, service):
            self.service = service

    @manager.factory(mapping=dict(service=Service), id=AnotherService)
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

    @manager.factory(use_arg_name=True, id=YetAnotherService)
    def injected_by_name_provider(test):
        return test

    assert s is container[YetAnotherService]

    with pytest.raises(ValueError):
        manager.factory(1)

    with pytest.raises(ValueError):
        @manager.factory
        class Test:
            pass


def test_factory_class():
    manager = DependencyManager()
    container = manager.container

    class Service(object):
        pass

    with pytest.raises(ValueError):
        @manager.factory
        class FaultyServiceProvider(object):
            def __call__(self):
                return Service()

    @manager.factory(id=Service)
    class ServiceProvider(object):
        def __call__(self):
            return Service()

    assert isinstance(container[Service], Service)
    # is a singleton
    assert container[Service] is container[Service]

    class AnotherService(object):
        def __init__(self, service):
            self.service = service

    @manager.factory(mapping=dict(service=Service), id=AnotherService)
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

    @manager.factory(use_arg_name=True, id=YetAnotherService)
    class YetAnotherServiceProvider(object):
        def __init__(self, test):
            self.test = test

        def __call__(self, test):
            assert self.test is test
            return test

    assert container['test'] is container[YetAnotherService]

    class OtherService(object):
        pass

    @manager.factory(use_arg_name=True,
                     mapping=dict(service=Service),
                     auto_wire=('__init__',),
                     id=OtherService)
    class OtherServiceProvider(object):
        def __init__(self, test, service):
            self.test = test
            self.service = service

        def __call__(self):
            return self.test, self.service

    output = container[OtherService]
    assert output[0] is container['test']
    assert isinstance(output[1], Service)