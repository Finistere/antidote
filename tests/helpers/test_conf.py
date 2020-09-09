import pytest

from antidote import world
from antidote.core import DependencyContainer
from antidote.helpers.constants import LazyConstantsMeta
from antidote.providers import LazyCallProvider, FactoryProvider


@pytest.fixture(autouse=True)
def test_world():
    with world.test.empty():
        c = world.get(DependencyContainer)
        c.register_provider(LazyCallProvider())
        c.register_provider(FactoryProvider())
        yield


def test_resource_meta():
    class Conf(metaclass=LazyConstantsMeta):
        A = 'a'
        B = 'b'

        def get(self, key):
            return key * 2

    assert 'aa' == world.get(Conf.A)
    assert 'bb' == world.get(Conf.B)

    conf = Conf()

    assert 'aa' == conf.A
    assert 'bb' == conf.B


def test_missing_get():
    with pytest.raises(ValueError):
        class Conf(metaclass=LazyConstantsMeta):
            A = 'a'


def test_private():
    class Conf(metaclass=LazyConstantsMeta):
        _A = 'a'

        b = 'b'

        def get(self, key):
            return key * 2

    conf = Conf()
    assert 'a' == conf._A
    assert 'b' == conf.b
