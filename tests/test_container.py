import pytest

from dep.container import Container
from dep.exceptions import *


def test_register():
    container = Container()

    @container.register()
    class S1:
        pass

    assert isinstance(container[S1], S1)

    s1 = object()
    container.register(s1, id='something')

    assert s1 == container['something']


def test_inject():
    container = Container()

    @container.register
    class S1:
        pass

    @container.inject
    def f3(x: S1):
        return x

    assert isinstance(f3(), S1)

    @container.inject
    def f4(x: S1, b=1):
        return x

    assert isinstance(f4(), S1)


def test_auto_wire():
    container = Container()

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


def test_no_name():
    container = Container()

    @container.register
    class SomeServiceN1:
        pass

    assert isinstance(container[SomeServiceN1], SomeServiceN1)


def test_no_duplicates():
    container = Container()

    @container.register(id='test')
    class Test:
        pass

    with pytest.raises(DuplicateServiceError):
        container.register(Test, id='test')

    with pytest.raises(DuplicateServiceError):
        container.register(object, id='test')


def test_override():
    container = Container()

    @container.register(id='test')
    class Test:
        pass

    assert isinstance(container['test'], Test)

    service = object()
    container['test'] = service
    assert service == container['test']


def test_service_instantiation_error():
    container = Container()

    @container.register
    class S1:
        def __init__(self, x):
            pass

    with pytest.raises(ServiceInstantiationError):
        _ = container[S1]


def test_service_with_default_values():
    container = Container()

    @container.register
    class S1:
        def __init__(self, x=1):
            pass

    assert isinstance(container[S1], S1)

