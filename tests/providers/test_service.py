import pytest

from antidote import world
from antidote.core.exceptions import DependencyNotFoundError
from antidote.exceptions import DuplicateDependencyError, FrozenWorldError
from antidote.providers.service import Build, ServiceProvider


@pytest.fixture()
def provider():
    with world.test.empty():
        world.provider(ServiceProvider)
        yield world.get(ServiceProvider)


class KeepInit:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class A(KeepInit):
    pass


class B(KeepInit):
    pass


@pytest.mark.parametrize(
    'wrapped,kwargs',
    [
        (1, {'test': 1}),
        (A, {'another': 'no'}),
        (A, {'not_hashable': {'hey': 'hey'}})
    ]
)
def test_build_str_repr(wrapped, kwargs):
    b = Build(wrapped, kwargs)

    # does not fail
    hash(b)

    assert repr(wrapped) in repr(b)
    assert repr(kwargs) in repr(b)


def test_build_eq_hash():
    a = Build(A, dict(test=1))
    assert hash(a) == hash(a)
    assert a == a

    a2 = Build(A, dict(test=1))
    assert hash(a) == hash(a2)
    assert a == a2

    for x in [Build(A, dict(test=2)),
              Build(A, dict(hey=1)),
              Build(1, dict(test=1))]:
        assert hash(a) != hash(x)
        assert a != x


def test_simple(provider: ServiceProvider):
    provider.register(A)
    assert isinstance(world.get(A), A)
    assert repr(A) in repr(provider)


@pytest.mark.parametrize('singleton', [True, False])
def test_register(singleton: bool):
    with world.test.empty():
        provider = ServiceProvider()
        provider.register(A, singleton=singleton)
        assert world.test.maybe_provide_from(provider, A).singleton is singleton
        assert isinstance(world.test.maybe_provide_from(provider, A).value, A)


def test_build(provider: ServiceProvider):
    provider.register(A)

    s = world.get(Build(A, dict(val=object)))
    assert isinstance(s, A)
    assert dict(val=object) == s.kwargs


def test_duplicate_error(provider: ServiceProvider):
    provider.register(A)

    with pytest.raises(DuplicateDependencyError):
        provider.register(A)


def test_invalid_type(provider: ServiceProvider):
    with pytest.raises(TypeError, match=".*service.*"):
        provider.register(object())

    with pytest.raises(TypeError, match=".*singleton.*"):
        provider.register(A, singleton=object())


@pytest.mark.parametrize('dependency', ['test', A, object()])
def test_unknown_dependency(dependency):
    with world.test.empty():
        provider = ServiceProvider()
        assert world.test.maybe_provide_from(provider, dependency) is None


@pytest.mark.parametrize('keep_singletons_cache', [True, False])
def test_copy(provider: ServiceProvider,
              keep_singletons_cache: bool):
    class C:
        pass

    world.singletons.set('factory', lambda: C())
    provider.register(A)

    cloned = provider.clone(keep_singletons_cache)
    if keep_singletons_cache:
        with world.test.clone(keep_singletons=True):
            assert isinstance(world.test.maybe_provide_from(cloned, A).value, A)
    else:
        with world.test.clone(keep_singletons=False):
            assert isinstance(world.test.maybe_provide_from(cloned, A).value, A)

    class D:
        pass

    class E:
        pass

    # changing original does not change cloned
    provider.register(D)
    assert isinstance(world.get(D), D)
    assert world.test.maybe_provide_from(cloned, D) is None

    # changing cloned does not change original
    cloned.register(E)
    assert isinstance(world.test.maybe_provide_from(cloned, E).value, E)
    with pytest.raises(DependencyNotFoundError):
        world.get(E)


def test_freeze(provider: ServiceProvider):
    world.freeze()

    with pytest.raises(FrozenWorldError):
        provider.register(A)


def test_exists(provider: ServiceProvider):
    provider.register(A)
    assert not provider.exists(object())
    assert provider.exists(A)
    assert provider.exists(Build(A, dict(a=1)))
    assert not provider.exists(Build(B, dict(a=1)))
