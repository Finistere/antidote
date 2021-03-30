import pytest

from antidote import Scope, world
from antidote._providers import FactoryProvider
from antidote._providers.service import Parameterized
from antidote.exceptions import (DependencyNotFoundError, DuplicateDependencyError,
                                 FrozenWorldError)


class A:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def build(**kwargs) -> A:
    return A(**kwargs)


@pytest.fixture()
def provider():
    with world.test.empty():
        world.test.singleton('lazy_build', build)
        world.provider(FactoryProvider)
        yield world.get(FactoryProvider)


@pytest.fixture(params=[dict(factory=build), dict(factory_dependency='lazy_build')])
def factory_params(request):
    return request.param


@pytest.fixture(params=[
    pytest.param(None, id='scope=None'),
    pytest.param(Scope.singleton(), id='scope=singleton')
])
def scope(request):
    return request.param


def test_str(provider: FactoryProvider, scope: Scope):
    provider.register(A, factory=build, scope=scope)
    assert 'A' in str(provider)
    assert 'build' in str(provider)


def test_simple(provider: FactoryProvider):
    factory_id = provider.register(A, factory=build, scope=Scope.singleton())
    assert isinstance(world.get(factory_id), A)
    # singleton
    assert world.get(factory_id) is world.get(factory_id)


def test_lazy(provider: FactoryProvider):
    world.test.singleton('A', build)
    factory_id = provider.register(A, factory_dependency='A', scope=Scope.singleton())
    assert isinstance(world.get(factory_id), A)
    # singleton
    assert world.get(factory_id) is world.get(factory_id)


def test_exists(scope: Scope, factory_params: dict):
    provider = FactoryProvider()
    factory_id = provider.register(A, scope=scope, **factory_params)

    assert not provider.exists(object())
    assert not provider.exists(Parameterized(object(), parameters=dict(a=1)))
    assert provider.exists(factory_id)
    assert provider.exists(Parameterized(factory_id, parameters=dict(a=1)))
    assert not provider.exists(A)
    assert not provider.exists(build)


@pytest.mark.parametrize('singleton', [True, False])
def test_singleton(provider: FactoryProvider, singleton: bool, factory_params: dict):
    scope = Scope.singleton() if singleton else None
    factory_id = provider.register(A, scope=scope, **factory_params)
    assert isinstance(world.get(factory_id), A)
    assert (world.get(factory_id) is world.get(factory_id)) == singleton


def test_multiple_factories(provider: FactoryProvider, scope: Scope):
    def build2(**kwargs) -> A:
        return A(**kwargs)

    b = provider.register(A, factory=build, scope=scope)
    b2 = provider.register(A, factory=build2, scope=scope)

    assert isinstance(world.get(b), A)
    assert isinstance(world.get(b2), A)


def test_duplicate_dependency(provider: FactoryProvider,
                              scope: Scope,
                              factory_params: dict):
    provider.register(A, scope=scope, **factory_params)
    with pytest.raises(DuplicateDependencyError):
        provider.register(A, scope=scope, **factory_params)


def test_parameterized_dependency(scope: Scope, factory_params: dict):
    with world.test.empty():
        world.test.singleton('lazy_build', build)
        provider = FactoryProvider()
        factory_id = provider.register(A, scope=scope, **factory_params)
        kwargs = dict(test=object())
        a = world.test.maybe_provide_from(provider,
                                          Parameterized(factory_id, kwargs)).unwrapped
        assert isinstance(a, A)
        assert a.kwargs == kwargs


def test_copy(scope: Scope):
    class B:
        pass

    class C:
        pass

    def build2() -> A:
        return A(build2=True)

    with world.test.empty():
        original = FactoryProvider()
        a_id = original.register(A, factory=build, scope=scope)

        # cloned has the same dependencies
        cloned = original.clone(False)
        with pytest.raises(DuplicateDependencyError):
            cloned.register(A, factory=build, scope=scope)
        assert isinstance(world.test.maybe_provide_from(cloned, a_id).unwrapped, A)

        # Adding dependencies to either original or cloned, should not impact the
        # other one.
        _ = original.register(B, factory=lambda: B(), scope=scope)
        _ = cloned.register(B, factory=lambda: B(), scope=scope)

        cloned.register(C, factory=lambda: C(), scope=scope)
        original.register(C, factory=lambda: C(), scope=scope)

    with world.test.empty():
        world.test.singleton('build', build)
        original = FactoryProvider()
        a_id = original.register(A, factory_dependency='build', scope=scope)
        a = world.test.maybe_provide_from(original, a_id).unwrapped

        assert isinstance(a, A)
        assert a.kwargs == {}

        cloned_with_singletons = original.clone(True)
        cloned = original.clone(False)
        with world.test.empty():
            world.test.singleton('build', build2)
            a2 = world.test.maybe_provide_from(cloned, a_id).unwrapped

            assert isinstance(a2, A)
            assert a2.kwargs == dict(build2=True)

            # We kept singletons, so previous dependency 'build' has been kept.
            a3 = world.test.maybe_provide_from(cloned_with_singletons, a_id).unwrapped
            assert isinstance(a3, A)
            assert a3.kwargs == {}


def test_freeze(provider: FactoryProvider, scope: Scope):
    world.freeze()

    with pytest.raises(FrozenWorldError):
        provider.register(A, factory=build, scope=scope)


def test_factory_id_repr(provider: FactoryProvider, scope: Scope):
    factory_id = provider.register(A, factory=build, scope=scope)
    assert f"{__name__}.A" in repr(factory_id)
    assert f"{__name__}.build" in repr(factory_id)

    class B:
        pass

    factory_id = provider.register(B, factory_dependency=build, scope=scope)
    assert f"{__name__}.test_factory_id_repr.<locals>.B" in repr(factory_id)
    assert f"{__name__}.build" in repr(factory_id)


def test_unknown_dependency(scope: Scope):
    p1 = FactoryProvider()
    assert world.test.maybe_provide_from(p1, object()) is None
    assert p1.maybe_debug(object()) is None

    p2 = FactoryProvider()
    dependency = p2.register(A, factory=build, scope=scope)
    assert world.test.maybe_provide_from(p1, dependency) is None
    assert p1.maybe_debug(dependency) is None


def test_invalid_lazy_dependency(scope: Scope):
    provider = FactoryProvider()
    fid = provider.register(A, factory_dependency="factory", scope=scope)

    with pytest.raises(DependencyNotFoundError, match=".*factory.*"):
        world.test.maybe_provide_from(provider, fid)


@pytest.mark.parametrize('output, factory, scope', [
    pytest.param(object(), build, None, id='output'),
    pytest.param(A, object(), None, id='factory'),
    pytest.param(A, build, object(), id='scope')
])
def test_sanity_checks(provider: FactoryProvider, output, factory, scope):
    with pytest.raises((AssertionError, TypeError)):
        provider.register(output, factory=factory, scope=scope)


def test_custom_scope(provider: FactoryProvider):
    dummy_scope = world.scopes.new(name='dummy')

    class MyService:
        pass

    fid = provider.register(MyService, factory=lambda: MyService(), scope=dummy_scope)
    my_service = world.get(fid)
    assert my_service is world.get(fid)
    world.scopes.reset(dummy_scope)
    assert my_service is not world.get(fid)
