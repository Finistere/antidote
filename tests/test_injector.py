import pytest

from dependency_manager import DependencyContainer, DependencyInjector


def test_build():
    container = DependencyContainer()
    builder = DependencyInjector(container)

    class Obj(object):
        def __init__(self, a, b):
            self.a = a
            self.b = b

    # arguments properly passed on
    s1 = builder.build(Obj, args=(1, 2))
    assert 1 == s1.a and 2 == s1.b

    s2 = builder.build(Obj, args=(1,), kwargs=dict(b=2))
    assert 1 == s2.a and 2 == s2.b

    s3 = builder.build(Obj, kwargs=dict(a=1, b=2))
    assert 1 == s3.a and 2 == s3.b


def test_call():
    container = DependencyContainer()
    builder = DependencyInjector(container)

    def f(a, b):
        return a, b

    # arguments properly passed on
    a, b = builder.call(f, args=(1, 2))
    assert 1 == a and 2 == b

    a, b = builder.call(f, args=(1,), kwargs=dict(b=2))
    assert 1 == a and 2 == b

    a, b = builder.call(f, kwargs=dict(a=1, b=2))
    assert 1 == a and 2 == b


def test_prepare():
    container = DependencyContainer()
    builder = DependencyInjector(container)

    def f(a, b):
        return a, b

    # arguments properly passed on
    a, b = builder.prepare(f, args=(1, 2))()
    assert 1 == a and 2 == b

    a, b = builder.prepare(f, args=(1,), kwargs=dict(b=2))()
    assert 1 == a and 2 == b

    a, b = builder.prepare(f, kwargs=dict(a=1, b=2))()
    assert 1 == a and 2 == b


def test_mapping():
    container = DependencyContainer()
    builder = DependencyInjector(container)

    class Service(object):
        pass

    container.register(Service, singleton=True)
    assert container[Service] is container[Service]

    def f(service):
        return service

    # function called properly
    assert container[Service] == builder.call(f, mapping=dict(service=Service))

    class Obj(object):
        def __init__(self, service, parameter=2):
            self.service = service
            self.parameter = parameter

    # object built properly
    s1 = builder.build(Obj, mapping=dict(service=Service))
    assert s1.service == container[Service]
    assert s1.parameter == 2

    # argument still passed on
    s2 = builder.build(Obj, mapping=dict(service=Service),
                       kwargs=dict(parameter=5))
    assert s2.service == container[Service]
    assert s2.parameter == 5

    class UnknownService(object):
        pass

    class AnotherObj(object):
        def __init__(self, service):
            self.service = service

    # with faulty mapping, raises the same as with no arguments
    with pytest.raises(TypeError):
        builder.build(AnotherObj, mapping=dict(service=UnknownService))


def test_use_arg_name():
    container = DependencyContainer()
    builder = DependencyInjector(container)

    container['test'] = object()

    def f(test):
        return test

    # test is inject by name
    assert container['test'] == builder.call(f, use_arg_name=True)

    class Obj(object):
        def __init__(self, test):
            self.test = test

    # test is inject by name
    obj = builder.build(Obj, use_arg_name=True)
    assert container['test'] == obj.test




