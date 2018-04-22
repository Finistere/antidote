import pytest

from antidote import (
    DependencyContainer, DependencyInjector,
    DependencyNotFoundError
)


@pytest.fixture()
def injector():
    container = DependencyContainer()
    injector = DependencyInjector(container)
    return injector


def test_bind(injector: DependencyInjector):
    def f(a, b):
        return a, b

    # arguments properly passed on
    a, b = injector.bind(f, args=(1, 2))()
    assert 1 == a and 2 == b

    a, b = injector.bind(f, args=(1,), kwargs=dict(b=2))()
    assert 1 == a and 2 == b

    a, b = injector.bind(f, kwargs=dict(a=1, b=2))()
    assert 1 == a and 2 == b


def test_call(injector: DependencyInjector):
    def f(a, b):
        return a, b

    # arguments properly passed on
    a, b = injector.call(f, args=(1, 2))
    assert 1 == a and 2 == b

    a, b = injector.call(f, args=(1,), kwargs=dict(b=2))
    assert 1 == a and 2 == b

    a, b = injector.call(f, kwargs=dict(a=1, b=2))
    assert 1 == a and 2 == b


def test_arg_map(injector: DependencyInjector):
    container = injector._container

    class Service(object):
        pass

    container[Service] = Service()

    def f(service):
        return service

    inject_mapping = injector.inject(arg_map=dict(service=Service))
    inject_sequence = injector.inject(arg_map=(Service,))

    # function called properly
    assert container[Service] is inject_mapping(f)()
    assert container[Service] is inject_sequence(f)()

    # function called properly
    assert inject_mapping(f)(None) is None
    assert inject_sequence(f)(None) is None

    def g(service, parameter=2):
        return service, parameter

    # argument still passed on
    assert (container[Service], 2) == inject_mapping(g)()
    assert (container[Service], 2) == inject_sequence(g)()

    class Obj(object):
        def __init__(self, service, parameter=2):
            self.service = service
            self.parameter = parameter

    class UnknownService(object):
        pass

    # faulty mapping
    inject_mapping = injector.inject(arg_map=dict(service=UnknownService))
    inject_sequence = injector.inject(arg_map=dict(service=UnknownService))
    with pytest.raises(DependencyNotFoundError):
        inject_mapping(f)()

    with pytest.raises(DependencyNotFoundError):
        inject_sequence(f)()

    # with no mapping, raises the same as with no arguments
    inject_mapping = injector.inject()
    with pytest.raises(TypeError):
        inject_mapping(f)()


def test_use_names(injector: DependencyInjector):
    container = injector._container

    container['test'] = object()

    def f(test):
        return test

    # test is inject by name
    f = injector.inject(func=f, use_names=True)
    assert container['test'] == f()

    container['yes'] = 'yes'
    container['no'] = 'no'

    def g(yes, no=None):
        return yes, no

    inject = injector.inject(use_names=('yes',))
    assert (container['yes'], None) == inject(g)()


def test_defaults(injector: DependencyInjector):
    container = injector._container

    container['service'] = object()

    def f(service, optional_service=None):
        return service, optional_service

    # test is inject by name
    inject = injector.inject(use_names=True)

    assert (container['service'], None) == inject(f)()

    container['optional_service'] = object()
    assert (container['service'], container['optional_service']) == inject(f)()


def test_method_wrapper_type_hints_error(monkeypatch,
                                         injector: DependencyInjector):
    def raises(*args, **kwargs):
        raise TypeError()

    monkeypatch.setattr('typing.get_type_hints', raises)

    def f():
        pass

    injector.inject(f)()


def test_repr(injector):
    assert repr(injector._container) in repr(injector)


@pytest.mark.parametrize(
    'method_name',
    [
        'bind',
        'inject',
        'call'
    ]
)
def test_value_error(method_name, injector: DependencyInjector):
    def f():
        pass

    with pytest.raises(ValueError):
        getattr(injector, method_name)(func=f, use_names=object())

    with pytest.raises(ValueError):
        getattr(injector, method_name)(func=f, arg_map=object())


def test_injection_order(injector: DependencyInjector):
    container = injector._container

    class Service:
        pass

    A = object()
    B = Service()
    C = object()
    container['A'] = A
    container[Service] = B
    container['C'] = C

    def f(A: Service):
        return A

    assert B is injector.inject(f)()
    assert A is injector.inject(f, use_names=True)()
    assert C is injector.inject(f, arg_map=['C'])()
    assert C is injector.inject(f, use_names=True, arg_map=['C'])()
