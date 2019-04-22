import pytest

from antidote.core import DependencyContainer
from antidote.helpers.resource import LazyConfigurationMeta
from antidote.providers import LazyCallProvider, ServiceProvider


@pytest.fixture()
def container():
    c = DependencyContainer()
    c.register_provider(LazyCallProvider(container=c))
    c.register_provider(ServiceProvider(container=c))

    return c


def test_resource_meta(container: DependencyContainer):
    class Conf(metaclass=LazyConfigurationMeta, container=container):
        A = 'a'
        B = 'b'

        def __call__(self, key):
            return key * 2

    assert 'aa' == container.get(Conf.A)
    assert 'bb' == container.get(Conf.B)

    conf = Conf()

    assert 'aa' == conf.A
    assert 'bb' == conf.B


def test_missing_get(container: DependencyContainer):
    with pytest.raises(ValueError):
        class Conf(metaclass=LazyConfigurationMeta, container=container):
            A = 'a'


def test_private(container: DependencyContainer):
    class Conf(metaclass=LazyConfigurationMeta, container=container):
        _A = 'a'

        b = 'b'

        def __call__(self, key):
            return key * 2

    conf = Conf()
    assert 'a' == conf._A
    assert 'b' == conf.b
