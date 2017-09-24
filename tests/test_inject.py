import pytest

from dep.container import ServicesContainer
from dep.exceptions import *


def test_auto_injection():
    container = ServicesContainer()

    @container.register(name='s1')
    class S1:
        pass

    @container.register(name='s2')
    class S2:
        def __init__(self, s1):
            self.s1 = s1

    @container.register(name='s3')
    class S3:
        def __init__(self, x: S1):
            self.s1 = x

    assert isinstance(container['s2'].s1, S1)
    assert isinstance(container['s3'].s1, S1)


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

