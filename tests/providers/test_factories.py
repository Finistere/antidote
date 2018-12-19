import pytest

from antidote import (
    DuplicateDependencyError, DependencyNotProvidableError, Dependency
)
from antidote.providers.factory import (FactoryProvider, Build)


class Service:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class AnotherService:
    def __init__(self, *args):
        pass


@pytest.fixture()
def provider():
    return FactoryProvider()


def test_register(provider: FactoryProvider):
    provider.register(Service, Service)

    dependency = provider.provide(Dependency(Service))
    assert isinstance(dependency.item, Service)
    assert repr(Service) in repr(provider)


def test_register_factory_id(provider: FactoryProvider):
    provider.register(Service, lambda: Service())

    dependency = provider.provide(Dependency(Service))
    assert isinstance(dependency.item, Service)


def test_singleton(provider: FactoryProvider):
    provider.register(Service, Service, singleton=True)
    provider.register(AnotherService, AnotherService, singleton=False)

    provide = provider.provide
    assert provide(Dependency(Service)).singleton is True
    assert provide(Dependency(AnotherService)).singleton is False


def test_takes_dependency_id(provider: FactoryProvider):
    provider.register(Service, lambda cls: cls(), takes_dependency_id=True)

    assert isinstance(
        provider.provide(Dependency(Service)).item,
        Service
    )

    assert provider.provide(Dependency(AnotherService)) is None


def test_build_dependency(provider: FactoryProvider):
    provider.register(Service, Service)

    s = provider.provide(Build(Service, 1, val=object)).item
    assert isinstance(s, Service)
    assert (1,) == s.args
    assert dict(val=object) == s.kwargs


def test_invalid_register_not_callable(provider: FactoryProvider):
    with pytest.raises(ValueError):
        provider.register(1, 1)


def test_invalid_register_id_null(provider: FactoryProvider):
    with pytest.raises(ValueError):
        provider.register(None, Service)


def test_duplicate_error(provider: FactoryProvider):
    provider.register(Service, Service)

    with pytest.raises(DuplicateDependencyError):
        provider.register(Service, Service)

    with pytest.raises(DuplicateDependencyError):
        provider.register(Service, lambda: Service())
