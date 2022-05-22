import pytest

from antidote import Scope, world
from antidote.lib.injectable._provider import Parameterized, InjectableProvider
from antidote.exceptions import DependencyNotFoundError, DuplicateDependencyError, FrozenWorldError


@pytest.fixture
def provider():
    with world.test.empty():
        world.provider(InjectableProvider)
        yield world.get(InjectableProvider)


@pytest.fixture(
    params=[
        pytest.param(None, id="scope=None"),
        pytest.param(Scope.singleton(), id="scope=singleton"),
    ]
)
def scope(request):
    return request.param


class KeepInit:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class A(KeepInit):
    pass


class B(KeepInit):
    pass


@pytest.mark.parametrize(
    "wrapped,kwargs",
    [(1, {"test": 1}), (A, {"another": "no"}), (A, {"not_hashable": {"hey": "hey"}})],
)
def test_parameterized_str_repr(wrapped, kwargs):
    b = Parameterized(wrapped, kwargs)

    # does not fail
    hash(b)

    assert repr(wrapped) in repr(b)
    assert repr(kwargs) in repr(b)


def test_parameterized_eq_hash():
    a = Parameterized(A, dict(test=1))
    assert hash(a) == hash(a)
    assert a == a

    a2 = Parameterized(A, dict(test=1))
    assert hash(a) == hash(a2)
    assert a == a2

    for x in [
        Parameterized(A, dict(test=2)),
        Parameterized(A, dict(hey=1)),
        Parameterized(1, dict(test=1)),
    ]:
        assert hash(a) != hash(x)
        assert a != x


def test_simple(provider: InjectableProvider, scope: Scope):
    provider.register(A, scope=scope)
    assert isinstance(world.get(A), A)
    assert repr(A) in repr(provider)


@pytest.mark.parametrize("singleton", [True, False])
def test_register(singleton: bool):
    with world.test.empty():
        provider = InjectableProvider()
        provider.register(A, scope=Scope.singleton() if singleton else None)
        assert world.test.maybe_provide_from(provider, A).is_singleton() is singleton
        assert isinstance(world.test.maybe_provide_from(provider, A).unwrapped, A)


def test_parameterized(scope: Scope):
    provider = InjectableProvider()
    provider.register(A, scope=scope)

    s = world.test.maybe_provide_from(provider, Parameterized(A, dict(val=object))).unwrapped
    assert isinstance(s, A)
    assert dict(val=object) == s.kwargs


def test_duplicate_error(provider: InjectableProvider, scope: Scope):
    provider.register(A, scope=scope)

    with pytest.raises(DuplicateDependencyError):
        provider.register(A, scope=scope)


@pytest.mark.parametrize("keep_singletons_cache", [True, False])
def test_copy(provider: InjectableProvider, keep_singletons_cache: bool, scope: Scope):
    class C:
        pass

    world.test.singleton("factory", lambda: C())
    provider.register(A, scope=scope)

    cloned = provider.clone(keep_singletons_cache)
    if keep_singletons_cache:
        with world.test.clone(keep_singletons=True):
            assert isinstance(world.test.maybe_provide_from(cloned, A).unwrapped, A)
    else:
        with world.test.clone(keep_singletons=False):
            assert isinstance(world.test.maybe_provide_from(cloned, A).unwrapped, A)

    class D:
        pass

    class E:
        pass

    # changing original does not change cloned
    provider.register(D, scope=scope)
    assert isinstance(world.get(D), D)
    assert world.test.maybe_provide_from(cloned, D) is None

    # changing cloned does not change original
    cloned.register(E, scope=scope)
    assert isinstance(world.test.maybe_provide_from(cloned, E).unwrapped, E)
    with pytest.raises(DependencyNotFoundError):
        world.get(E)


def test_freeze(provider: InjectableProvider, scope: Scope):
    world.freeze()

    with pytest.raises(FrozenWorldError):
        provider.register(A, scope=scope)


def test_exists(provider: InjectableProvider, scope: Scope):
    provider.register(A, scope=scope)
    assert not provider.exists(object())
    assert provider.exists(A)
    assert provider.exists(Parameterized(A, dict(a=1)))
    assert not provider.exists(Parameterized(B, dict(a=1)))


def test_custom_scope(provider: InjectableProvider):
    dummy_scope = world.scopes.new(name="dummy")

    class MyService:
        pass

    provider.register(MyService, scope=dummy_scope)

    my_service = world.get(MyService)
    assert my_service is world.get(MyService)
    world.scopes.reset(dummy_scope)
    assert my_service is not world.get(MyService)


@pytest.mark.parametrize(
    "klass, scope",
    [pytest.param(object(), None, id="klass"), pytest.param(A, object(), id="scope")],
)
def test_sanity_checks(provider: InjectableProvider, klass, scope):
    with pytest.raises((AssertionError, TypeError)):
        provider.register(klass, scope=scope)
