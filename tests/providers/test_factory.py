import pytest

from antidote import world
from antidote.core import DependencyContainer
from antidote.core.exceptions import FrozenWorldError
from antidote.exceptions import DuplicateDependencyError
from antidote.providers.factory import Build, FactoryProvider


class Service:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class AnotherService(Service):
    pass


@pytest.fixture()
def provider():
    with world.test.empty():
        provider = FactoryProvider()
        world.get(DependencyContainer).register_provider(provider)
        yield provider


@pytest.mark.parametrize(
    'wrapped,kwargs',
    [
        (1, {'test': 1}),
        (Service, {'another': 'no'}),
        (Service, {'not_hashable': {'hey': 'hey'}})
    ]
)
def test_build_eq_hash(wrapped, kwargs):
    b = Build(wrapped, **kwargs)

    # does not fail
    hash(b)

    for f in (lambda e: e, hash):
        assert f(Build(wrapped, **kwargs)) == f(b)

    assert repr(wrapped) in repr(b)
    assert repr(kwargs) in repr(b)


@pytest.mark.parametrize(
    'args,kwargs',
    [
        [(), {}],
        [(1,), {}],
        [(), {'test': 1}],
    ]
)
def test_invalid_build(args: tuple, kwargs: dict):
    with pytest.raises(TypeError):
        Build(*args, **kwargs)


def test_simple(provider: FactoryProvider):
    provider.register_class(Service)

    dependency = provider.world_provide(Service)
    assert isinstance(dependency.instance, Service)
    assert repr(Service) in repr(provider)


def test_singleton(provider: FactoryProvider):
    provider.register_class(Service, singleton=True)
    provider.register_class(AnotherService, singleton=False)

    assert provider.world_provide(Service).singleton is True
    assert provider.world_provide(AnotherService).singleton is False


def test_takes_dependency(provider: FactoryProvider):
    provider.register_factory(factory=lambda cls: cls(), dependency=Service,
                              takes_dependency=True)

    assert isinstance(provider.world_provide(Service).instance, Service)
    assert provider.world_provide(AnotherService) is None


def test_build(provider: FactoryProvider):
    provider.register_class(Service)

    s = provider.world_provide(Build(Service, val=object)).instance
    assert isinstance(s, Service)
    assert dict(val=object) == s.kwargs

    provider.register_factory(AnotherService, factory=AnotherService,
                              takes_dependency=True)

    s = provider.world_provide(Build(AnotherService, val=object)).instance
    assert isinstance(s, AnotherService)
    assert (AnotherService,) == s.args
    assert dict(val=object) == s.kwargs


def test_non_singleton_factory(provider: FactoryProvider):
    def factory_builder():
        def factory(o=object()):
            return o

        return factory

    provider.register_factory('factory', factory=factory_builder, singleton=False)
    provider.register_providable_factory('service', factory_dependency='factory')

    service = provider.world_provide('service').instance
    assert provider.world_provide('service').instance is not service


def test_duplicate_error(provider: FactoryProvider):
    provider.register_class(Service)

    with pytest.raises(DuplicateDependencyError):
        provider.register_class(Service)

    with pytest.raises(DuplicateDependencyError):
        provider.register_factory(factory=lambda: Service(), dependency=Service)

    with pytest.raises(DuplicateDependencyError):
        provider.register_providable_factory(factory_dependency='dummy',
                                             dependency=Service)


@pytest.mark.parametrize(
    'kwargs',
    [dict(factory='test', dependency=Service),
     dict(factory=object(), dependency=Service)]
)
def test_invalid_type(provider: FactoryProvider, kwargs):
    with pytest.raises(TypeError):
        provider.register_factory(**kwargs)


@pytest.mark.parametrize('dependency', ['test', Service, object()])
def test_unknown_dependency(provider: FactoryProvider, dependency):
    assert provider.world_provide(dependency) is None


def test_clone(provider: FactoryProvider):
    class Service2:
        pass

    class Service3:
        pass

    provider.register_class(Service)
    provider.register_factory(Service2, lambda: Service2())
    world.singletons.set("factory", lambda: Service3())
    provider.register_providable_factory(Service3, "factory")

    cloned = provider.clone()
    assert isinstance(cloned.world_provide(Service).instance, Service)
    assert isinstance(cloned.world_provide(Service2).instance, Service2)
    assert isinstance(cloned.world_provide(Service3).instance, Service3)

    class Service4:
        pass

    cloned.register_class(Service4)
    assert isinstance(cloned.world_provide(Service4).instance, Service4)
    assert provider.world_provide(Service4) is None


def test_freeze(provider: FactoryProvider):
    provider.freeze()

    with pytest.raises(FrozenWorldError):
        provider.register_class(Service)

    with pytest.raises(FrozenWorldError):
        provider.register_factory(Service, lambda: Service())

    with pytest.raises(FrozenWorldError):
        provider.register_providable_factory(Service, "dummy")
