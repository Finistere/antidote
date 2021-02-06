import pytest

from antidote import Constants, Wiring, const, world
from antidote._providers import LazyProvider, ServiceProvider
from antidote.core.exceptions import DependencyInstantiationError
from antidote.exceptions import DependencyNotFoundError


class A:
    pass


@pytest.fixture(autouse=True)
def test_world():
    with world.test.empty():
        world.provider(LazyProvider)
        world.provider(ServiceProvider)
        yield


def test_simple():
    class Config(Constants):
        A = const('a')
        B = const('b')

        def provide_const(self, name, arg):
            return arg * 2

    assert world.get(Config.A) == 'aa'
    assert world.get(Config.B) == 'bb'

    conf = Config()
    assert conf.A == 'aa'
    assert conf.B == 'bb'


def test_default():
    a = object()
    b = object()

    class Config(Constants):
        # exists
        A = const('a')
        # default
        B = const('b', default=b)
        # nothing
        C = const('c')
        # different error
        D = const('d', default='x')

        def provide_const(self, name, arg):
            if arg == 'd':
                raise Exception()
            return dict(a=a)[arg]

    assert world.get(Config.A) is a
    assert world.get(Config.B) is b
    with pytest.raises(DependencyInstantiationError):
        world.get(Config.C)
    with pytest.raises(DependencyInstantiationError):
        world.get(Config.D)

    class Config(Constants):
        with pytest.raises(TypeError):
            X = const[A](default='x')


def test_auto_cast():
    class AutoCast(Constants):
        __antidote__ = Constants.Conf(auto_cast=True)
        A = const[int]('109')
        B = const[float]('3.14')
        C = const[str](199)

    assert AutoCast().A == 109
    assert AutoCast().B == 3.14
    assert AutoCast().C == '199'

    assert world.get(AutoCast.A) == 109
    assert world.get(AutoCast.B) == 3.14
    assert world.get(AutoCast.C) == '199'

    #######

    class LimitedAutoCast(Constants):
        __antidote__ = Constants.Conf(auto_cast=[int, float])
        A = const[int]('109')
        B = const[float]('3.14')
        C = const[str](199)

    assert LimitedAutoCast().A == 109
    assert LimitedAutoCast().B == 3.14

    with pytest.raises(TypeError, match=".*C.*"):
        LimitedAutoCast().C

    assert world.get(LimitedAutoCast.A) == 109
    assert world.get(LimitedAutoCast.B) == 3.14

    with pytest.raises(DependencyInstantiationError, match=".*C.*"):
        world.get(LimitedAutoCast.C)

    #######

    class NoAutoCast(Constants):
        __antidote__ = Constants.Conf(auto_cast=False)
        A = const[int]('109')
        B = const[float]('3.14')
        C = const[str](199)

    with pytest.raises(TypeError, match=".*A.*"):
        NoAutoCast().A

    with pytest.raises(TypeError, match=".*B.*"):
        NoAutoCast().B

    with pytest.raises(TypeError, match=".*C.*"):
        NoAutoCast().C

    #######

    class MetaDummy:
        def __new__(cls, *args, **kwargs):
            raise RuntimeError()

    class ImpossibleCast(Constants):
        __antidote__ = Constants.Conf(auto_cast=[MetaDummy])
        A = const[MetaDummy]('x')

    with pytest.raises(RuntimeError):
        ImpossibleCast().A

    with pytest.raises(DependencyInstantiationError):
        world.get(ImpossibleCast.A)


def test_type_safety():
    class MetaDummy:
        def __new__(cls, *args, **kwargs):
            return object()

    class Config(Constants):
        __antidote__ = Constants.Conf(auto_cast=[MetaDummy])
        INVALID = const[int]('109')
        INVALID_CAST = const[MetaDummy]('x')

    with pytest.raises(TypeError, match=".*INVALID.*"):
        Config().INVALID

    with pytest.raises(TypeError, match=".*INVALID_CAST.*"):
        Config().INVALID_CAST

    with pytest.raises(DependencyInstantiationError):
        world.get(Config.INVALID)

    with pytest.raises(DependencyInstantiationError):
        world.get(Config.INVALID_CAST)


def test_name():
    class Config(Constants):
        A = const()
        B = const()

        def provide_const(self, name, arg):
            return name

    assert world.get(Config.A) == 'A'
    assert world.get(Config.B) == 'B'
    conf = Config()
    assert conf.A == 'A'
    assert conf.B == 'B'


def test_default_get():
    class Config(Constants):
        NOTHING = const()
        B = const("B")

    with pytest.raises(DependencyInstantiationError):
        world.get(Config.NOTHING)

    with pytest.raises(ValueError, match=".*NOTHING.*"):
        Config().NOTHING

    assert world.get(Config.B) == 'B'
    assert Config().B == "B"


def test_no_const():
    class Config(Constants):
        A = 'a'

        def provide_const(self, name, arg):
            return arg * 2

    with pytest.raises(DependencyNotFoundError):
        world.get(Config.A)

    conf = Config()
    assert conf.A == 'a'


def test_no_get_method():
    class Config(Constants):
        A = const('a')

    assert world.get(Config.A) == 'a'


def test_invalid_conf():
    with pytest.raises(TypeError, match=".*__antidote__.*"):
        class Config(Constants):
            __antidote__ = object()


def test_no_subclass_of_constants():
    class Dummy(Constants):
        pass

    with pytest.raises(TypeError, match=".*abstract.*"):
        class SubDummy(Dummy):
            pass


@pytest.mark.parametrize('kwargs, expectation', [
    (dict(wiring=object()), pytest.raises(TypeError, match=".*wiring.*")),
    (dict(auto_cast=object()), pytest.raises(TypeError, match=".*auto_cast.*")),
    (dict(auto_cast=['1']), pytest.raises(TypeError, match=".*auto_cast.*")),
])
def test_conf_error(kwargs, expectation):
    with expectation:
        Constants.Conf(**kwargs)


@pytest.mark.parametrize('kwargs', [
    dict(wiring=Wiring(methods=['method'])),
    dict(auto_cast=frozenset((str,))),
])
def test_conf_copy(kwargs):
    conf = Constants.Conf().copy(**kwargs)
    for k, v in kwargs.items():
        assert getattr(conf, k) == v


def test_conf_repr():
    conf = Constants.Conf()
    assert "auto_cast" in repr(conf)
