import pytest

from antidote import world
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

    dependency = provider.test_provide(A)
    assert isinstance(dependency.instance, A)
    assert repr(A) in repr(provider)


@pytest.mark.parametrize('singleton', [True, False])
def test_register(provider: ServiceProvider, singleton: bool):
    provider.register(A, singleton=singleton)
    assert provider.test_provide(A).singleton is singleton
    assert isinstance(provider.test_provide(A).instance, A)


@pytest.mark.parametrize('singleton', [True, False])
@pytest.mark.parametrize('factory', [lambda: A(), world.lazy('factory')])
def test_register_with_factory(provider: ServiceProvider, singleton: bool, factory):
    world.singletons.set('factory', lambda: A())
    provider.register_with_factory(A, factory=factory, singleton=singleton)
    assert provider.test_provide(A).singleton is singleton
    assert isinstance(provider.test_provide(A).instance, A)


def test_takes_dependency(provider: ServiceProvider):
    provider.register_with_factory(A, factory=lambda cls: cls(), takes_dependency=True)
    assert isinstance(provider.test_provide(A).instance, A)
    assert provider.test_provide(B) is None


def test_build(provider: ServiceProvider):
    provider.register(A)

    s = provider.test_provide(Build(A, dict(val=object))).instance
    assert isinstance(s, A)
    assert dict(val=object) == s.kwargs

    provider.register_with_factory(B, factory=B,
                                   takes_dependency=True)

    s = provider.test_provide(Build(B, dict(val=object))).instance
    assert isinstance(s, B)
    assert (B,) == s.args
    assert dict(val=object) == s.kwargs


def test_non_singleton_factory(provider: ServiceProvider):
    class Factory:
        def __init__(self):
            self.counter = 0

        def __call__(self):
            self.counter += 1
            return A(id=self.counter)

    provider.register(Factory)
    provider.register_with_factory(A, factory=world.lazy(Factory))

    a = provider.test_provide(A).instance
    assert isinstance(a, A)
    assert a.kwargs == dict(id=1)

    a2 = provider.test_provide(A).instance
    assert isinstance(a2, A)
    assert a2.kwargs == dict(id=2)


def test_duplicate_error(provider: ServiceProvider):
    provider.register(A)

    with pytest.raises(DuplicateDependencyError):
        provider.register(A)

    with pytest.raises(DuplicateDependencyError):
        provider.register_with_factory(A, factory=lambda: A())

    with pytest.raises(DuplicateDependencyError):
        provider.register_with_factory(A, factory=world.lazy('dummy'))


def test_invalid_type(provider: ServiceProvider):
    with pytest.raises(TypeError, match=".*service.*"):
        provider.register(object())

    with pytest.raises(TypeError, match=".*service.*"):
        provider.register_with_factory(object(), factory=lambda: A())

    with pytest.raises(TypeError, match=".*factory.*"):
        provider.register_with_factory(A, factory=object())

    with pytest.raises(TypeError, match=".*singleton.*"):
        provider.register_with_factory(A, factory=lambda: A(), singleton=object())

    with pytest.raises(TypeError, match=".*takes_dependency.*"):
        provider.register_with_factory(A, factory=lambda: A(), takes_dependency=object())


@pytest.mark.parametrize('dependency', ['test', A, object()])
def test_unknown_dependency(provider: ServiceProvider, dependency):
    assert provider.test_provide(dependency) is None


@pytest.mark.parametrize('keep_singletons_cache', [True, False])
def test_copy(provider: ServiceProvider,
              keep_singletons_cache: bool):
    class C:
        pass

    class C2:
        pass

    world.singletons.set('factory', lambda: C())
    provider.register(A)
    provider.register_with_factory(B, factory=lambda: B())
    provider.register_with_factory(C, factory=world.lazy('factory'))

    cloned = provider.clone(keep_singletons_cache)
    if keep_singletons_cache:
        with world.test.clone(keep_singletons=True):
            assert isinstance(cloned.test_provide(A).instance, A)
            assert isinstance(cloned.test_provide(B).instance, B)
            assert isinstance(cloned.test_provide(C).instance, C)
    else:
        with world.test.clone(keep_singletons=False):
            world.singletons.set('factory', lambda: C2())
            assert isinstance(cloned.test_provide(A).instance, A)
            assert isinstance(cloned.test_provide(B).instance, B)
            assert isinstance(cloned.test_provide(C).instance, C2)

    class D:
        pass

    class E:
        pass

    # changing original does not change cloned
    provider.register(D)
    assert isinstance(provider.test_provide(D).instance, D)
    assert cloned.test_provide(D) is None

    # changing cloned does not change original
    cloned.register(E)
    assert isinstance(cloned.test_provide(E).instance, E)
    assert provider.test_provide(E) is None


def test_freeze(provider: ServiceProvider):
    world.freeze()

    with pytest.raises(FrozenWorldError):
        provider.register(A)

    with pytest.raises(FrozenWorldError):
        provider.register_with_factory(A, lambda: A())
