import pytest

from antidote import const, Constants, Wiring, world
from antidote.exceptions import DependencyNotFoundError
from antidote.providers import LazyProvider, ServiceProvider


class A:
    pass


@pytest.fixture(autouse=True)
def test_world():
    with world.test.empty():
        world.provider(LazyProvider)
        world.provider(ServiceProvider)
        yield


def test_lazy_constants():
    class Config(Constants):
        A = 'a'
        B = 'b'

        def get(self, key):
            return key * 2

    assert world.get(Config.A) == 'aa'
    assert world.get(Config.B) == 'bb'

    conf = Config()
    assert conf.A == 'aa'
    assert conf.B == 'bb'


def test_no_rule():
    class Config(Constants):
        __antidote__ = Constants.Conf(is_const=None)
        A = 'a'

        def get(self, key):
            return key * 2

    with pytest.raises(DependencyNotFoundError):
        world.get(Config.A)

    conf = Config()
    assert conf.A == 'a'


def test_custom_rule():
    class Config(Constants):
        __antidote__ = Constants.Conf(is_const=lambda name: name.startswith('hello'))
        A = 'a'
        helloA = 'a'

        def get(self, key):
            return key * 2

    assert world.get(Config.helloA) == 'aa'
    with pytest.raises(DependencyNotFoundError):
        world.get(Config.A)

    conf = Config()
    assert conf.A == 'a'
    assert conf.helloA == 'aa'


def test_const():
    class Config(Constants):
        __antidote__ = Constants.Conf(is_const=None)

        a = const('1')
        b = const[int]('2')

        def get(self, key):
            return int(key)

    assert world.get(Config.a) == 1
    assert world.get(Config.b) == 2

    conf = Config()
    assert conf.a == 1
    assert conf.b == 2


def test_invalid_lazy_method():
    with pytest.raises(TypeError):
        class Config(Constants):
            A = 'a'

    with pytest.raises(TypeError):
        class Config(Constants):
            A = 'a'
            get = 1


def test_private_attribute():
    class Config(Constants):
        _A = 'a'
        b = 'b'

        def get(self, key):
            return key * 2

    conf = Config()
    assert 'a' == conf._A
    assert 'b' == conf.b


def test_public():
    with world.test.clone():
        class Config(Constants):
            def get(self, key):
                return key

        with pytest.raises(DependencyNotFoundError):
            world.get(Config)

    with world.test.clone():
        class Config(Constants):
            __antidote__ = Constants.Conf(public=False)

            def get(self, key):
                return key

        with pytest.raises(DependencyNotFoundError):
            world.get(Config)

    with world.test.clone():
        class Config(Constants):
            __antidote__ = Constants.Conf(public=True)

            def get(self, key):
                return key

        assert isinstance(world.get(Config), Config)


def test_invalid_conf():
    with pytest.raises(TypeError, match=".*__antidote__.*"):
        class Config(Constants):
            __antidote__ = object()

            def get(self, key):
                pass


def test_no_subclass_of_service():
    class Dummy(Constants):
        def get(self, key):
            pass

    with pytest.raises(TypeError, match=".*abstract.*"):
        class SubDummy(Dummy):
            def get(self, key):
                pass


@pytest.mark.parametrize('kwargs, expectation', [
    (dict(wiring=object()), pytest.raises(TypeError, match=".*wiring.*")),
    (dict(is_const=object()), pytest.raises(TypeError, match=".*is_const.*")),
    (dict(public=object()), pytest.raises(TypeError, match=".*public.*")),
])
def test_conf_error(kwargs, expectation):
    with expectation:
        Constants.Conf(**kwargs)


@pytest.mark.parametrize('kwargs', [
    dict(wiring=Wiring(methods=['method'])),
    dict(public=True),
    dict(is_const=lambda name: False),
])
def test_conf_copy(kwargs):
    conf = Constants.Conf().copy(**kwargs)
    for k, v in kwargs.items():
        assert getattr(conf, k) == v
