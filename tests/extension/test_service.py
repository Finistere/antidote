from contextlib import contextmanager

import pytest

from antidote import Service, Wiring, service, world, Provide
from antidote._providers import ServiceProvider
from antidote.exceptions import DuplicateDependencyError


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(autouse=True)
def test_world():
    with world.test.empty():
        world.provider(ServiceProvider)
        yield


def test_register_simple():
    @service
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
    @service(singleton=True)
    class Singleton:
        pass

    assert world.get(Singleton) is world.get(Singleton)

    @service(singleton=False)
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


def test_custom_scope():
    dummy_scope = world.scopes.new(name='dummy')

    class Scoped(Service):
        __antidote__ = Service.Conf(scope=dummy_scope)

    my_service = world.get(Scoped)
    assert world.get(Scoped) is my_service
    world.scopes.reset(dummy_scope)
    assert world.get(Scoped) is not my_service

    @service(scope=dummy_scope)
    class Scoped:
        pass

    my_service = world.get(Scoped)
    assert world.get(Scoped) is my_service
    world.scopes.reset(dummy_scope)
    assert world.get(Scoped) is not my_service


def test_parameterized():
    x = object()

    class A(Service):
        __antidote__ = Service.Conf(parameters=['x'])

        def __init__(self, **kwargs):
            self.kwargs = kwargs

    a = world.get(A.parameterized(x=x))
    assert a.kwargs == dict(x=x)

    with pytest.raises(ValueError, match=".*parameters.*'x'.*"):
        A.parameterized()

    with pytest.raises(ValueError, match=".*parameters.*'x'.*"):
        A.parameterized(unknown='something')


def test_not_parametrized():
    class A(Service):
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    with pytest.raises(RuntimeError, match=".*parameters.*"):
        A.parameterized(x=1)


def test_invalid_with_default_parameters():
    with pytest.raises(ValueError, match=".*default.*"):
        class A(Service):
            __antidote__ = Service.Conf(parameters=['x'])

            def __init__(self, x: str = 'default'):
                self.x = x


def test_invalid_with_injected_parameters():
    class A(Service):
        pass

    with pytest.raises(ValueError, match=".*injected.*class.*A.*"):
        class B(Service):
            __antidote__ = Service.Conf(parameters=['x'])

            def __init__(self, x: Provide[A]):
                self.x = x


def test_duplicate_registration():
    with pytest.raises(DuplicateDependencyError):
        @service
        class Dummy(Service):
            pass


@pytest.mark.parametrize('cls', ['test', object(), lambda: None])
def test_invalid_class(cls):
    with pytest.raises(TypeError):
        service(cls)


@pytest.mark.parametrize(
    'kwargs,expectation',
    [
        (dict(tags=object()), pytest.raises(TypeError, match=".*tags.*")),
        (dict(tags=['test']), pytest.raises(TypeError, match=".*tags.*")),
        (dict(singleton=object()), pytest.raises(TypeError, match=".*singleton.*")),
        (dict(scope=object()), pytest.raises(TypeError, match=".*scope.*")),
    ]
)
def test_invalid_service_args(kwargs, expectation):
    with expectation:
        @service(**kwargs)
        class Dummy:
            method = None


def test_no_subclass_of_service():
    class A(Service):
        pass

    with pytest.raises(TypeError, match=".*abstract.*"):
        class B(A):
            pass


def test_invalid_conf():
    with pytest.raises(TypeError, match=".*__antidote__.*"):
        class Dummy(Service):
            __antidote__ = object()


@pytest.mark.parametrize('expectation, parameters', [
    (pytest.raises(TypeError), "string"),
    (pytest.raises(TypeError), object()),
    (pytest.raises(TypeError), [1]),
    (does_not_raise(), ['x']),
    (does_not_raise(), []),
    (does_not_raise(), None),
])
def test_conf_parameters(expectation, parameters):
    with expectation:
        class A(Service):
            __antidote__ = Service.Conf(parameters=parameters)


@pytest.mark.parametrize('expectation, kwargs', [
    pytest.param(pytest.raises(TypeError, match=f'.*{arg}.*'),
                 {arg: object()},
                 id=arg)
    for arg in ['wiring',
                'singleton',
                'scope',
                'parameters']
])
def test_invalid_conf_args(kwargs, expectation):
    with expectation:
        Service.Conf(**kwargs)


@pytest.mark.parametrize('kwargs', [
    dict(singleton=False),
    dict(scope=None),
    dict(wiring=Wiring(methods=['method'])),
    dict(parameters=frozenset(['x']))
])
def test_conf_copy(kwargs):
    conf = Service.Conf(singleton=True).copy(**kwargs)
    for k, v in kwargs.items():
        assert getattr(conf, k) == v


def test_invalid_copy():
    conf = Service.Conf()
    with pytest.raises(TypeError, match=".*both.*"):
        conf.copy(singleton=False, scope=None)


def test_conf_repr():
    conf = Service.Conf()
    assert "scope" in repr(conf)
