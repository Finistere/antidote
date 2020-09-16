import pytest

from antidote import world
from antidote.exceptions import DuplicateDependencyError, FrozenWorldError
from antidote.providers.factory import FactoryProvider
from antidote.providers.service import Build


@pytest.fixture()
def provider():
    with world.test.empty():
        world.provider(FactoryProvider)
        yield world.get(FactoryProvider)


class A:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def build(**kwargs) -> A:
    return A(**kwargs)


def test_str(provider: FactoryProvider):
    provider.register(A, build)
    assert str(A) in str(provider)
    assert str(build) in str(provider)


def test_simple(provider: FactoryProvider):
    factory_id = provider.register(A, build)
    assert isinstance(world.get(factory_id), A)
    # singleton
    assert world.get(factory_id) is world.get(factory_id)


def test_lazy(provider: FactoryProvider):
    world.singletons.set('A', build)
    factory_id = provider.register(A, world.lazy('A'))
    assert isinstance(world.get(factory_id), A)
    # singleton
    assert world.get(factory_id) is world.get(factory_id)


@pytest.mark.parametrize('singleton', [True, False])
def test_singleton(singleton: bool):
    with world.test.empty():
        world.singletons.set('A', build)
        world.provider(FactoryProvider)
        with world.test.clone():
            provider = world.get(FactoryProvider)
            factory_id = provider.register(A, build, singleton=singleton)
            assert isinstance(world.get(factory_id), A)
            assert (world.get(factory_id) is world.get(factory_id)) == singleton

        with world.test.clone(keep_singletons=True):
            provider = world.get(FactoryProvider)
            factory_id = provider.register(A, world.lazy('A'), singleton=singleton)
            assert isinstance(world.get(factory_id), A)
            assert (world.get(factory_id) is world.get(factory_id)) == singleton


@pytest.mark.parametrize('first', ['register', 'register_lazy'])
@pytest.mark.parametrize('second', ['register', 'register_lazy'])
def test_duplicate_dependency(provider: FactoryProvider, first: str, second: str):
    world.singletons.set('A', build)

    if first == 'register':
        provider.register(A, build)
    else:
        provider.register(A, world.lazy('A'))

    with pytest.raises(DuplicateDependencyError):
        if second == 'register':
            provider.register(A, build)
        else:
            provider.register(A, world.lazy('A'))


def test_invalid_register(provider: FactoryProvider):
    with pytest.raises(TypeError):
        provider.register(A, 1)


def test_build_dependency(provider: FactoryProvider):
    world.singletons.set('A', build)
    kwargs = dict(test=object())

    with world.test.clone():
        provider = world.get(FactoryProvider)
        factory_id = provider.register(A, build)
        a = world.get(Build(factory_id, kwargs))
        assert isinstance(a, A)
        assert a.kwargs == kwargs

    with world.test.clone(keep_singletons=True):
        provider = world.get(FactoryProvider)
        factory_id = provider.register(A, world.lazy('A'))
        a = world.get(Build(factory_id, kwargs))
        assert isinstance(a, A)
        assert a.kwargs == kwargs


def test_copy():
    class B:
        pass

    class C:
        pass

    def build2() -> A:
        return A(build2=True)

    with world.test.empty():
        original = FactoryProvider()
        a_id = original.register(A, build)

        # cloned has the same dependencies
        cloned = original.clone(keep_singletons_cache=False)
        with pytest.raises(DuplicateDependencyError):
            cloned.register(A, build)
        assert isinstance(cloned.test_provide(a_id).instance, A)

        # Adding dependencies to either original or cloned, should not impact the
        # other one.
        original_b_id = original.register(B, lambda: B())
        cloned_b_id = cloned.register(B, lambda: B())

        cloned.register(C, lambda: C())
        original.register(C, lambda: C())

    with world.test.empty():
        world.singletons.set('build', build)
        original = FactoryProvider()
        a_id = original.register(A, world.lazy('build'))
        a = original.test_provide(a_id).instance

        assert isinstance(a, A)
        assert a.kwargs == {}

        cloned_with_singletons = original.clone(keep_singletons_cache=True)
        cloned = original.clone(keep_singletons_cache=False)
        with world.test.empty():
            world.singletons.set('build', build2)
            a2 = cloned.test_provide(a_id).instance

            assert isinstance(a2, A)
            assert a2.kwargs == dict(build2=True)

            # We kept singletons, so previous dependency 'build' has been kept.
            a3 = cloned_with_singletons.test_provide(a_id).instance
            assert isinstance(a3, A)
            assert a3.kwargs == {}


def test_freeze(provider: FactoryProvider):
    world.freeze()

    with pytest.raises(FrozenWorldError):
        provider.register(A, build)


def test_factory_id_repr(provider: FactoryProvider):
    factory_id = provider.register(A, build)
    assert repr(A) in repr(factory_id)
    assert repr(build) in repr(factory_id)

    class B:
        pass

    factory_id = provider.register(B, world.lazy(build))
    assert repr(B) in repr(factory_id)
    assert repr(build) in repr(factory_id)


def test_invalid_dependency(provider: FactoryProvider):
    assert provider.test_provide(object()) is None

    p2 = FactoryProvider()
    dependency = p2.register(A, build)
    assert provider.test_provide(dependency) is None
