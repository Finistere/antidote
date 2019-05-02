import pytest

from antidote.core import DependencyContainer
from antidote.helpers.constants import LazyConstantsMeta
from antidote.providers import LazyCallProvider, FactoryProvider


@pytest.fixture()
def container():
    c = DependencyContainer()
    c.register_provider(LazyCallProvider(container=c))
    c.register_provider(FactoryProvider(container=c))

    return c


def test_resource_meta(container: DependencyContainer):
    class Conf(metaclass=LazyConstantsMeta, container=container):
        A = 'a'
        B = 'b'

        def get(self, key):
            return key * 2

    assert 'aa' == container.get(Conf.A)
    assert 'bb' == container.get(Conf.B)

    conf = Conf()

    assert 'aa' == conf.A
    assert 'bb' == conf.B


def test_missing_get(container: DependencyContainer):
    with pytest.raises(ValueError):
        class Conf(metaclass=LazyConstantsMeta, container=container):
            A = 'a'


def test_private(container: DependencyContainer):
    class Conf(metaclass=LazyConstantsMeta, container=container):
        _A = 'a'

        b = 'b'

        def get(self, key):
            return key * 2

    conf = Conf()
    assert 'a' == conf._A
    assert 'b' == conf.b
