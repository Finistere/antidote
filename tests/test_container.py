import pytest

from dep.container import ServicesContainer
from dep.exceptions import *


def test_register():
    container = ServicesContainer()

    @container.register()
    class S1:
        pass

    assert isinstance(container[S1], S1)

    s1 = object()
    container.register(s1, id='something')

    assert s1 == container['something']

    s2 = object()
    container.register(s2)

    assert s2 == container['s2']


def test_inject():
    container = ServicesContainer()

    @container.register
    class S1:
        pass

    @container.inject(use_name=True)
    def f1(s1):
        return s1

    assert isinstance(f1(), S1)

    @container.inject
    def f3(x: S1):
        return x

    assert isinstance(f3(), S1)

    @container.inject(use_name=False)
    def f4(x: S1, b=1):
        return x

    assert isinstance(f4(), S1)


def test_auto_wire():
    container = ServicesContainer()

    @container.register(id='s1')
    class S1:
        pass

    @container.register(id='s2')
    class S2:
        def __init__(self, s1: S1):
            self.s1 = s1

    @container.register(id='s3', auto_wire=False)
    class S3(S2):
        pass

    assert isinstance(container['s2'].s1, S1)

    with pytest.raises(ServiceInstantiationError):
        _ = container['s3']


def test_no_name(monkeypatch):
    container = ServicesContainer()

    something = object()
    container.register(something)
    assert something == container['something']

    other_thing = object()
    container.register(service=other_thing)
    assert other_thing == container['other_thing']

    thing1 = object()
    thing2 = object()
    with pytest.raises(ValueError):
        container.register(thing1);container.register(thing2)

    @container.register
    class SomeServiceN1:
        pass

    assert isinstance(container['SomeServiceN1'], SomeServiceN1)
    assert isinstance(container['some_service_n1'], SomeServiceN1)

    def dummy(*args, **kwargs):
        raise Exception()

    monkeypatch.setattr(container, '_guess_name_from_caller_code', dummy)

    thing3 = object()
    with pytest.raises(ValueError):
        container.register(thing3)


def test_no_duplicates():
    container = ServicesContainer()

    @container.register(id='test')
    class Test:
        pass

    with pytest.raises(DuplicateServiceError):
        container.register(Test)

    with pytest.raises(DuplicateServiceError):
        container.register(object, id='test')

    with pytest.raises(DuplicateServiceError):
        class Test:
            pass
        container.register(Test)


def test_override():
    container = ServicesContainer()

    @container.register(id='test')
    class Test:
        pass

    assert isinstance(container['test'], Test)

    service = object()
    container['test'] = service
    assert service == container['test']


def test_service_instantiation_error():
    container = ServicesContainer()

    @container.register
    class S1:
        def __init__(self, x):
            pass

    with pytest.raises(ServiceInstantiationError):
        _ = container[S1]


def test_service_with_default_values():
    container = ServicesContainer()

    @container.register
    class S1:
        def __init__(self, x=1):
            pass

    assert isinstance(container[S1], S1)

