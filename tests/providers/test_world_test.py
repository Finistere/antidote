import pytest

from antidote import world
from antidote._providers import WorldTestProvider
from antidote.core import DependencyValue, Scope
from antidote.exceptions import (DuplicateDependencyError)


class Service:
    pass


class AnotherService:
    pass


@pytest.fixture()
def provider():
    with world.test.empty():
        yield world.get(WorldTestProvider)


def test_singleton(provider: WorldTestProvider):
    s = Service()
    assert not provider.exists(Service)

    provider.add_singletons({Service: s})
    assert world.get(Service) is s
    assert provider.exists(Service)


def test_factory(provider: WorldTestProvider):
    s = Service()

    assert not provider.exists(Service)
    provider.add_factory(Service, factory=lambda: s, scope=None)

    assert world.get(Service) is s
    assert provider.exists(Service)


def test_factory_singleton(provider: WorldTestProvider):
    provider.add_factory(Service, factory=lambda: Service(), scope=Scope.singleton())
    assert world.get(Service) is world.get(Service)


def test_factory_no_scope(provider: WorldTestProvider):
    provider.add_factory(Service, factory=lambda: Service(), scope=None)
    assert world.get(Service) is not world.get(Service)


def test_factory_scope(provider: WorldTestProvider):
    scope = world.scopes.new(name='dummy')
    provider.add_factory(Service, factory=lambda: Service(), scope=scope)

    s = world.get(Service)
    assert world.get(Service) is s

    world.scopes.reset(scope)
    assert world.get(Service) is not s


def test_duplicate():
    with world.test.empty():
        provider = world.get(WorldTestProvider)
        provider.add_singletons({Service: Service()})

        with pytest.raises(DuplicateDependencyError):
            provider.add_singletons({Service: Service()})

        with pytest.raises(DuplicateDependencyError):
            provider.add_factory(Service, factory=lambda: Service(), scope=None)

    with world.test.new():
        provider = world.get(WorldTestProvider)
        provider.add_factory(Service, factory=lambda: Service(), scope=None)

        with pytest.raises(DuplicateDependencyError):
            provider.add_singletons({Service: Service()})

        with pytest.raises(DuplicateDependencyError):
            provider.add_factory(Service, factory=lambda: Service(), scope=None)


def test_clone(provider: WorldTestProvider):
    s = Service()
    a_s = AnotherService()
    provider.add_singletons({Service: s})
    provider.add_factory(AnotherService, factory=lambda: a_s, scope=Scope.singleton())

    def d(x):
        return DependencyValue(x, scope=Scope.singleton())

    clone = provider.clone(keep_singletons_cache=True)
    assert world.test.maybe_provide_from(clone, Service) == d(s)
    assert world.test.maybe_provide_from(clone, AnotherService) == d(a_s)

    clone_without_singletons = provider.clone(keep_singletons_cache=False)
    assert world.test.maybe_provide_from(clone_without_singletons, Service) is None
    assert world.test.maybe_provide_from(clone_without_singletons,
                                         AnotherService) == d(a_s)
