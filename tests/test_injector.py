import pytest

from dependency_manager import DependencyContainer, DependencyInjector, \
    DependencyNotFoundError


def test_prepare():
    container = DependencyContainer()
    injector = DependencyInjector(container)

    def f(a, b):
        return a, b

    # arguments properly passed on
    a, b = injector.prepare(f, args=(1, 2))()
    assert 1 == a and 2 == b

    a, b = injector.prepare(f, args=(1,), kwargs=dict(b=2))()
    assert 1 == a and 2 == b

    a, b = injector.prepare(f, kwargs=dict(a=1, b=2))()
    assert 1 == a and 2 == b


def test_mapping():
    container = DependencyContainer()
    injector = DependencyInjector(container)

    class Service(object):
        pass

    container.register(Service, singleton=True)
    assert container[Service] is container[Service]

    def f(service):
        return service

    inject = injector.inject(mapping=dict(service=Service))

    # function called properly
    assert container[Service] is inject(f)()

    # function called properly
    assert inject(f)(None) is None

    def g(service, parameter=2):
        return service, parameter

    # argument still passed on
    assert (container[Service], 2) == inject(g)()

    class Obj(object):
        def __init__(self, service, parameter=2):
            self.service = service
            self.parameter = parameter

    class UnknownService(object):
        pass

    # faulty mapping
    inject = injector.inject(mapping=dict(service=UnknownService))
    with pytest.raises(DependencyNotFoundError):
        inject(f)()

    # with no mapping, raises the same as with no arguments
    inject = injector.inject()
    with pytest.raises(TypeError):
        inject(f)()


def test_use_arg_name():
    container = DependencyContainer()
    injector = DependencyInjector(container)

    container['test'] = object()

    def f(test):
        return test

    # test is inject by name
    inject = injector.inject(use_arg_name=True)
    assert container['test'] == inject(f)()


def test_defaults():
    container = DependencyContainer()
    injector = DependencyInjector(container)

    container['service'] = object()

    def f(service, optional_service=None):
        return service, optional_service

    # test is inject by name
    inject = injector.inject(use_arg_name=True)

    assert (container['service'], None) == inject(f)()

    container['optional_service'] = object()
    assert (container['service'], container['optional_service']) == inject(f)()
