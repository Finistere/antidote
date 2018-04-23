from configparser import RawConfigParser
from operator import getitem

import pytest

from antidote import (
    DependencyContainer, DependencyInjector, DependencyInstantiationError,
    DependencyManager, DependencyNotFoundError, DependencyNotProvidableError,
    Instance
)
from antidote.providers import FactoryProvider, ParameterProvider


def test_inject_bind():
    manager = DependencyManager()
    container = manager.container

    class Service(object):
        pass

    manager.register(Service)

    @manager.inject(bind=True)
    def f(x):
        return x

    with pytest.raises(TypeError):
        f()

    @manager.inject(arg_map=dict(x=Service), bind=True)
    def g(x):
        return x

    assert container[Service] is g()

    # arguments are bound, so one should not be able to pass injected
    # argument.
    with pytest.raises(TypeError):
        g(1)

    container['service'] = container[Service]
    container['service_bis'] = container[Service]

    @manager.inject(use_names=True, bind=True)
    def h(service, service_bis=None):
        return service, service_bis

    result = h()
    assert container[Service] is result[0]
    assert container[Service] is result[1]

    @manager.inject(use_names=('service',), bind=True)
    def h(service, service_bis=None):
        return service, service_bis

    result = h()
    assert container[Service] is result[0]
    assert None is result[1]


def test_inject_with_mapping():
    manager = DependencyManager()
    container = manager.container

    class Service(object):
        pass

    manager.register(Service)

    class AnotherService(object):
        pass

    manager.register(AnotherService)

    @manager.inject
    def f(x):
        return x

    with pytest.raises(TypeError):
        f()

    @manager.inject(arg_map=dict(x=Service))
    def g(x):
        return x

    assert container[Service] is g()

    @manager.inject(arg_map=(Service,))
    def g(x):
        return x

    assert container[Service] is g()

    @manager.inject(arg_map=dict(x=Service))
    def h(x, b=1):
        return x

    assert container[Service] is h()

    @manager.inject(arg_map=(Service,))
    def h(x, b=1):
        return x

    assert container[Service] is h()

    manager.arg_map = dict(x=Service, y=AnotherService)

    @manager.inject
    def u(x, y):
        return x, y

    assert container[Service] is u()[0]
    assert container[AnotherService] is u()[1]

    @manager.inject(arg_map=dict(y=Service))
    def v(x, y):
        return x, y

    assert container[Service] is v()[0]
    assert container[Service] is v()[1]

    @manager.inject(arg_map=(AnotherService,))
    def v(x, y):
        return x, y

    assert container[AnotherService] is v()[0]
    assert container[AnotherService] is v()[1]


def test_wire():
    manager = DependencyManager()
    container = manager.container

    class Service(object):
        pass

    class AnotherService(object):
        pass

    manager.register(Service)
    manager.register(AnotherService)

    @manager.wire(arg_map=dict(service=Service,
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


def test_use_names():
    manager = DependencyManager(use_names=False)
    container = manager.container

    _service = object()
    _service_bis = object()
    container['service'] = _service
    container['service_bis'] = _service_bis

    def f(service):
        return service

    with pytest.raises(TypeError):
        manager.inject(f)()

    def g(service, service_bis=None, something=None):
        return service, service_bis, something

    g_result = manager.inject(use_names=True)(g)()
    assert _service is g_result[0]
    assert _service_bis is g_result[1]
    assert None is g_result[2]

    g_result = manager.inject(use_names=('service',))(g)()
    assert _service is g_result[0]
    assert None is g_result[1]
    assert None is g_result[2]

    # use names for every injection by default.
    manager.use_names = True

    assert _service is manager.inject(f)()

    with pytest.raises(TypeError):
        manager.inject(use_names=False)(f)()


def test_register():
    manager = DependencyManager(auto_wire=True)
    container = manager.container

    @manager.register
    class Service(object):
        pass

    assert isinstance(container[Service], Service)

    @manager.register(arg_map=dict(service=Service))
    class AnotherService(object):
        def __init__(self, service):
            self.service = service

    assert isinstance(container[AnotherService], AnotherService)
    assert container[Service] is container[AnotherService].service
    # singleton
    assert container[AnotherService] is container[AnotherService]

    container['service'] = object()

    @manager.register(use_names=True)
    class YetAnotherService(object):
        def __init__(self, service):
            self.service = service

    assert isinstance(container[YetAnotherService], YetAnotherService)
    assert container['service'] is container[YetAnotherService].service
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
        container[BrokenService]

    @manager.register(auto_wire=('__init__', 'method'),
                      arg_map=dict(service=Service,
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
        manager.register(object())

    def f():
        pass

    with pytest.raises(ValueError):
        manager.register(f)


def test_factory_function():
    manager = DependencyManager()
    container = manager.container

    class Service(object):
        pass

    with pytest.raises(ValueError):
        @manager.factory
        def faulty_service_provider():
            return Service()

    @manager.factory(dependency_id=Service)
    def service_provider():
        return Service()

    assert isinstance(container[Service], Service)
    # is a singleton
    assert container[Service] is container[Service]

    class AnotherService(object):
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

    @manager.factory(dependency_id=Service)
    class ServiceProvider(object):
        def __call__(self):
            return Service()

    assert isinstance(container[Service], Service)
    # is a singleton
    assert container[Service] is container[Service]

    class AnotherService(object):
        def __init__(self, service):
            self.service = service

    @manager.factory(arg_map=dict(service=Service),
                     dependency_id=AnotherService)
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

    @manager.factory(use_names=True, dependency_id=YetAnotherService)
    class YetAnotherServiceProvider(object):
        def __init__(self, test):
            self.test = test

        def __call__(self, test):
            assert self.test is test
            return test

    assert container['test'] is container[YetAnotherService]

    class OtherService(object):
        pass

    @manager.factory(use_names=True,
                     arg_map=dict(service=Service),
                     auto_wire=('__init__',),
                     dependency_id=OtherService)
    class OtherServiceProvider(object):
        def __init__(self, test, service):
            self.test = test
            self.service = service

        def __call__(self):
            return self.test, self.service

    output = container[OtherService]
    assert output[0] is container['test']
    assert isinstance(output[1], Service)


def test_provider():
    manager = DependencyManager()
    container = manager.container

    container['service'] = object()

    @manager.provider(use_names=True)
    class DummyProvider(object):
        def __init__(self, service=None):
            self.service = service

        def __antidote_provide__(self, dependency):
            if dependency.id == 'test':
                return Instance(dependency.id)
            else:
                raise DependencyNotProvidableError(dependency)

    assert isinstance(container.providers[DummyProvider], DummyProvider)
    assert container.providers[DummyProvider].service is container['service']
    assert 'test' == container['test']

    with pytest.raises(DependencyNotFoundError):
        container['test2']

    with pytest.raises(ValueError):
        manager.provider(object())

    with pytest.raises(ValueError):
        @manager.provider
        class MissingAntidoteProvideMethod(object):
            pass

    with pytest.raises(TypeError):
        @manager.provider(auto_wire=False)
        class MissingDependencyProvider(object):
            def __init__(self, service):
                self.service = service

            def __antidote_provide__(self, dependency):
                return Instance(dependency.id)


def test_providers():
    manager = DependencyManager()

    assert 2 == len(manager.providers)
    assert FactoryProvider in manager.providers
    assert ParameterProvider in manager.providers

    @manager.provider
    class DummyProvider(object):
        def __antidote_provide__(self, dependency):
            return Instance(1)

    assert DummyProvider in manager.providers


def test_parameters():
    manager = DependencyManager()
    container = manager.container

    manager.register_parameters({'test1': 'some value'}, getter=getitem)
    assert 'some value' == container['test1']

    manager.register_parameters({'test2': 'another value'}, getter=getitem,
                                prefix='conf:')
    assert 'another value' == container['conf:test2']

    manager.register_parameters({'test3': {'nested': 'yes'}}, getter=getitem,
                                split='.')
    assert 'yes' == container['test3.nested']

    manager.register_parameters({'param': '1', 'paramb': {'test': 2}},
                                getter=getitem, prefix='params:', split='.')

    assert '1' == container['params:param']
    assert 2 == container['params:paramb.test']

    with pytest.raises(DependencyNotFoundError):
        container[object()]

    with pytest.raises(DependencyNotFoundError):
        container['test3.nested.yes']


def test_register_parameters_custom_getter():
    manager = DependencyManager()
    container = manager.container

    @manager.register_parameters({'a': {'b': {'c': 99}}})
    def parser(obj, item):
        from functools import reduce
        if isinstance(item, str):
            return reduce(getitem, list(item), obj)

        raise LookupError(item)

    assert 99 == container['abc']

    # Does not fail with missing dependency
    with pytest.raises(DependencyNotFoundError):
        container[object()]


def test_invalid_arguments():
    manager = DependencyManager()

    with pytest.raises(ValueError):
        manager.register_parameters(object(), getter=object())

    with pytest.raises(ValueError):
        manager.register_parameters(object(), prefix=object())

    with pytest.raises(ValueError):
        manager.register_parameters(object(), split=object())


def test_parameters_with_configparser():
    manager = DependencyManager()
    container = manager.container

    cfg = RawConfigParser()
    cfg.add_section('test')
    cfg.set('test', 'param', '100')

    manager.register_parameters(cfg, getter=getitem, split='.')

    assert '100' == container['test.param']

    with pytest.raises(DependencyNotFoundError):
        container['section.option']

    with pytest.raises(DependencyNotFoundError):
        container['test.option']

    with pytest.raises(DependencyNotFoundError):
        container['test.param.test']


def test_manager_repr():
    manager = DependencyManager()

    assert repr(manager.container) in repr(manager)
    assert repr(manager.injector) in repr(manager)
    assert 'auto_wire' in repr(manager)
    assert 'use_names' in repr(manager)
    assert 'mapping' in repr(manager)


def test_context():
    manager = DependencyManager()
    manager.container['param'] = 1

    with manager.context(include=[]):
        with pytest.raises(DependencyNotFoundError):
            manager.container['param']

        manager.container[DependencyInjector]
        manager.container[DependencyContainer]

    with manager.context(include=['param']):
        assert 1 == manager.container['param']

        manager.container[DependencyInjector]
        manager.container[DependencyContainer]

    with manager.context(exclude=['param']):
        with pytest.raises(DependencyNotFoundError):
            manager.container['param']

        manager.container[DependencyInjector]
        manager.container[DependencyContainer]

    with manager.context(missing=['param']):
        with pytest.raises(DependencyNotFoundError):
            manager.container['param']

        manager.container[DependencyInjector]
        manager.container[DependencyContainer]

    with manager.context(dependencies={'param': 2}):
        assert 2 == manager.container['param']

        manager.container[DependencyInjector]
        manager.container[DependencyContainer]
