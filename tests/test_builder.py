import pytest

from blood.container import ServiceContainer, Builder
from blood.exceptions import *


def test_build():
    container = ServiceContainer()
    builder = Builder(container)

    class Obj(object):
        def __init__(self, a, b):
            self.a = a
            self.b = b

    s1 = builder.build(Obj, args=(1, 2))
    assert 1 == s1.a and 2 == s1.b

    s2 = builder.build(Obj, args=(1,), kwargs=dict(b=2))
    assert 1 == s2.a and 2 == s2.b

    s3 = builder.build(Obj, kwargs=dict(a=1, b=2))
    assert 1 == s3.a and 2 == s3.b

    class Service:
        pass

    container.register(Service)

    s4 = builder.build(Obj, mapping=dict(a=Service), kwargs=dict(b=2))
    assert isinstance(s4.a, Service) and s4.b == 2


def test_call():
    container = ServiceContainer()
    builder = Builder(container)

    def f(a, b):
        return a, b

    a, b = builder.call(f, args=(1, 2))
    assert 1 == a and 2 == b

    a, b = builder.call(f, args=(1,), kwargs=dict(b=2))
    assert 1 == a and 2 == b

    a, b = builder.call(f, kwargs=dict(a=1, b=2))
    assert 1 == a and 2 == b

    class Service:
        pass

    container.register(Service)

    a, b = builder.call(f, mapping=dict(a=Service), kwargs=dict(b=2))
    assert isinstance(a, Service) and b == 2


def test_mapping():
    container = ServiceContainer()
    builder = Builder(container)

    class Service(object):
        pass

    container.register(Service, singleton=True)

    class Obj(object):
        def __init__(self, service, parameter=2):
            self.service = service
            self.parameter = parameter

    s1 = builder.build(Obj, mapping=dict(service=Service))
    assert s1.service == container[Service]
    assert s1.parameter == 2

    s2 = builder.build(Obj, mapping=dict(service=Service),
                       kwargs=dict(parameter=5))
    assert s2.service == container[Service]
    assert s2.parameter == 5

    class UnknownService(object):
        pass

    class AnotherObj(object):
        def __init__(self, service):
            self.service = service

    with pytest.raises(TypeError):
        builder.build(AnotherObj, mapping=dict(service=UnknownService))

