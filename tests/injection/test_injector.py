import functools

import pytest

from antidote import DependencyContainer, DependencyNotFoundError, inject
from antidote.exceptions import UndefinedContainerError


# def test_bind():
#     def f(a, b):
#         return a, b
#
#     # arguments properly passed on
#     a, b = bind(f, args=(1, 2))()
#     assert 1 == a and 2 == b
#
#     a, b = bind(f, args=(1,), kwargs=dict(b=2))()
#     assert 1 == a and 2 == b
#
#     a, b = bind(f, kwargs=dict(a=1, b=2))()
#     assert 1 == a and 2 == b
#
#
# def test_call(injector: DependencyInjector):
#     def f(a, b):
#         return a, b
#
#     # arguments properly passed on
#     a, b = call(f, args=(1, 2))
#     assert 1 == a and 2 == b
#
#     a, b = call(f, args=(1,), kwargs=dict(b=2))
#     assert 1 == a and 2 == b
#
#     a, b = call(f, kwargs=dict(a=1, b=2))
#     assert 1 == a and 2 == b


# def test_undefined_container():
#     @inject(container=DependencyContainer())
#     def f(x):
#         return x
#
#     with pytest.raises(UndefinedContainerError):
#         f()


def test_arg_map():
    container = DependencyContainer()
    inject_ = functools.partial(inject, container=container)

    class Service:
        pass

    container[Service] = Service()

    def f(service):
        return service

    inject_mapping = inject_(arg_map=dict(service=Service))
    inject_sequence = inject_(arg_map=(Service,))

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

    class UnknownService:
        pass

    # faulty mapping
    inject_mapping = inject_(arg_map=dict(service=UnknownService))
    inject_sequence = inject_(arg_map=dict(service=UnknownService))
    with pytest.raises(DependencyNotFoundError):
        inject_mapping(f)()

    with pytest.raises(DependencyNotFoundError):
        inject_sequence(f)()

    # with no mapping, raises the same as with no arguments
    inject_mapping = inject_()
    with pytest.raises(TypeError):
        inject_mapping(f)()


def test_use_names():
    container = DependencyContainer()
    inject_ = functools.partial(inject, container=container)

    container['test'] = object()

    def f(test):
        return test

    # test is inject by name
    assert container['test'] == inject_(f, use_names=True)()

    container['yes'] = 'yes'
    container['no'] = 'no'

    def g(yes, no=None):
        return yes, no

    assert (container['yes'], None) == inject_(g, use_names=['yes'])()


def test_use_type_hints():
    container = DependencyContainer()
    inject_ = functools.partial(inject, container=container)

    class Service:
        pass

    class AnotherService:
        pass

    container[Service] = Service()
    container[AnotherService] = AnotherService()

    def f(service: Service):
        return service

    assert container[Service] == inject_(f)()
    assert container[Service] == inject_(f, use_type_hints=True)()

    with pytest.raises(TypeError):
        inject_(f, use_type_hints=False)()

    container['yes'] = 'yes'
    container['no'] = 'no'

    def g(service: Service, another_service: AnotherService = None):
        return service, another_service

    inj = inject_(use_type_hints=['service'])
    assert (container[Service], None) == inj(g)()


def test_defaults():
    container = DependencyContainer()
    container['service'] = object()

    def f(service, optional_service=None):
        return service, optional_service

    # test is inject by name
    inj = inject(use_names=True, container=container)

    assert (container['service'], None) == inj(f)()

    container['optional_service'] = object()
    assert (container['service'], container['optional_service']) == inj(f)()


def test_method_wrapper_type_hints_error(monkeypatch):
    container = DependencyContainer()

    def raises(*args, **kwargs):
        raise TypeError()

    monkeypatch.setattr('typing.get_type_hints', raises)

    def f():
        pass

    inject(f, container=container)()


def test_invalid_argument():
    def f():
        pass

    with pytest.raises(ValueError):
        inject(func=f, arg_map=object())

    with pytest.raises(ValueError):
        inject(func=f, use_names=object())

    with pytest.raises(ValueError):
        inject(func=f, use_type_hints=object())


def test_injection_order():
    container = DependencyContainer()
    inject_ = functools.partial(inject, container=container)

    class Service:
        pass

    by_name = object()
    by_type_hints = Service()
    by_arg_map = object()
    container['A'] = by_name
    container[Service] = by_type_hints
    container['C'] = by_arg_map

    def f(A: Service):
        return A

    def g(A):
        return A

    assert by_type_hints is inject_(f)()
    assert by_type_hints is inject_(f, use_names=True)()
    assert by_name is inject_(g, use_names=True)()
    assert by_arg_map is inject_(f, arg_map=['C'])()
    assert by_arg_map is inject_(f, use_names=True, arg_map=['C'])()
