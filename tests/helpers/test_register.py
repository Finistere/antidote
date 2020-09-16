from contextlib import contextmanager

import pytest

from antidote import register, Service, Tag, Wiring, world
from antidote.exceptions import DuplicateDependencyError
from antidote.providers import ServiceProvider


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(autouse=True)
def test_world():
    with world.test.empty():
        world.provider(ServiceProvider)
        yield


def test_register_simple():
    @register
    class A:
        pass

    assert isinstance(world.get(A), A)
    # singleton by default
    assert world.get(A) is world.get(A)


def test_simple():
    class A(Service):
        pass

    assert isinstance(world.get(A), A)
    # singleton by default
    assert world.get(A) is world.get(A)


def test_register_singleton():
    @register(singleton=True)
    class Singleton:
        pass

    assert world.get(Singleton) is world.get(Singleton)

    @register(singleton=False)
    class NoScope:
        pass

    assert world.get(NoScope) != world.get(NoScope)


def test_singleton():
    class Singleton(Service):
        __antidote__ = Service.Conf(singleton=True)

    assert world.get(Singleton) is world.get(Singleton)

    class NoScope(Service):
        __antidote__ = Service.Conf(singleton=False)

    assert world.get(NoScope) != world.get(NoScope)


@pytest.mark.parametrize(
    'factory',
    [lambda cls: cls(None),
     'class_build',
     None]
)
def test_factory(factory):
    world.singletons.set('hello', object())

    @register(factory=factory, dependencies=['hello'])
    class Dummy:
        def __init__(self, x=None):
            self.x = x

        @classmethod
        def class_build(cls, x):
            return cls(x)

    assert isinstance(world.get(Dummy), Dummy)
    if isinstance(factory, str):
        assert world.get(Dummy).x is world.get('hello')

    class Dummy2(Service):
        __antidote__ = Service.Conf(factory=factory).with_wiring(dependencies=['hello'])

        def __init__(self, x=None):
            self.x = x

        @classmethod
        def class_build(cls, x):
            return cls(x)

    assert isinstance(world.get(Dummy2), Dummy2)
    if isinstance(factory, str):
        assert world.get(Dummy2).x is world.get('hello')


def test_register_factory_dependency():
    @register(factory=world.lazy('factory'))
    class A:
        pass

    world.singletons.update(dict(factory=lambda cls: dict(service=cls())))
    assert isinstance(world.get(A), dict)
    assert isinstance(world.get(A)['service'], A)


def test_factory_dependency():
    class A(Service):
        __antidote__ = Service.Conf(factory=world.lazy('factory'))

    world.singletons.update(dict(factory=lambda cls: dict(service=cls())))
    assert isinstance(world.get(A), dict)
    assert isinstance(world.get(A)['service'], A)


def test_duplicate_registration():
    with pytest.raises(DuplicateDependencyError):
        @register
        class Dummy(Service):
            pass


@pytest.mark.parametrize('cls', ['test', object(), lambda: None])
def test_invalid_class(cls):
    with pytest.raises(TypeError):
        register(cls)


@pytest.mark.parametrize(
    'kwargs,expectation',
    [
        (dict(factory=object()), pytest.raises(TypeError, match=".*factory.*")),
        (dict(auto_wire=object()), pytest.raises(TypeError, match=".*auto_wire.*")),
        (dict(auto_wire=['test', object()]),
         pytest.raises(TypeError, match=".*auto_wire.*")),
        (dict(factory='method', auto_wire=False),
         pytest.raises(TypeError, match=".*method.*")),
        (dict(auto_wire='method'), pytest.raises(TypeError, match=".*method.*")),
        (dict(auto_wire=['method']), pytest.raises(TypeError, match=".*method.*")),
        (dict(tags=object()), pytest.raises(TypeError, match=".*tags.*")),
        (dict(tags=['test']), pytest.raises(TypeError, match=".*tags.*")),
        (dict(singleton=object()), pytest.raises(TypeError, match=".*singleton.*")),
        (dict(dependencies=object()), pytest.raises(TypeError, match=".*dependencies.*")),
        (dict(use_names=object()), pytest.raises(TypeError, match=".*use_names.*")),
        (dict(use_type_hints=object()),
         pytest.raises(TypeError, match=".*use_type_hints.*")),
    ]
)
def test_invalid_params(kwargs, expectation):
    with expectation:
        @register(**kwargs)
        class Dummy:
            method = None


def test_invalid_factory_super_wiring():
    class Dummy:
        @classmethod
        def build(cls):
            return cls()

    with pytest.raises(ValueError, match=".*factory.*wire_super.*"):
        @register(factory='build', wire_super=False)
        class SubDummy(Dummy):
            pass

    class Dummy2(Service, abstract=True):
        __antidote__ = Service.Conf(factory='build', wiring=Wiring(methods=['build']))

        @classmethod
        def build(cls):
            return cls()

    with pytest.raises(ValueError, match=".*factory.*wire_super.*"):
        class SubDummy2(Dummy2):
            pass


def test_not_tags():
    with world.test.empty():
        world.provider(ServiceProvider)

        @register
        class A:
            pass

        assert isinstance(world.get(A), A)
        assert world.get(A) is world.get(A)

        class B(Service):
            pass

        assert isinstance(world.get(B), B)
        assert world.get(B) is world.get(B)

    with world.test.empty():
        world.provider(ServiceProvider)
        tag = Tag()
        with pytest.raises(RuntimeError):
            @register(tags=[tag])
            class A:
                pass

        with pytest.raises(RuntimeError):
            class B(Service):
                __antidote__ = Service.Conf(tags=[tag])


def test_invalid_conf():
    with pytest.raises(TypeError, match=".*__antidote__.*"):
        class Dummy(Service):
            __antidote__ = 1


def test_no_subclass_of_service():
    class A(Service):
        pass

    with pytest.raises(TypeError, match=".*abstract.*"):
        class B(A):
            pass


@pytest.mark.parametrize('kwargs, expectation', [
    (dict(singleton=object()), pytest.raises(TypeError, match=".*singleton.*")),
    (dict(tags=object()), pytest.raises(TypeError, match=".*tags.*")),
    (dict(tags=['dummy']), pytest.raises(TypeError, match=".*tags.*")),
    (dict(wiring=object()), pytest.raises(TypeError, match=".*wiring.*")),
    (dict(factory=object()), pytest.raises(TypeError, match=".*factory.*")),
])
def test_conf_error(kwargs, expectation):
    with expectation:
        Service.Conf(**kwargs)


@pytest.mark.parametrize('kwargs', [
    dict(singleton=False),
    dict(tags=(Tag(),)),
    dict(wiring=Wiring(methods=['method'])),
    dict(factory=lambda cls: cls)
])
def test_conf_copy(kwargs):
    conf = Service.Conf(singleton=True, tags=[], factory=None).copy(**kwargs)
    for k, v in kwargs.items():
        assert getattr(conf, k) == v
