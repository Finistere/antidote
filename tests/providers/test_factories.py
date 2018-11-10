import pytest

from antidote import (
    DependencyDuplicateError, DependencyNotProvidableError
)
from antidote.providers.factories import (Dependency, DependencyFactory,
                                          FactoryProvider, Build)


class Service:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class ServiceSubclass(Service):
    pass


class AnotherService:
    def __init__(self, *args):
        pass


@pytest.fixture()
def provider():
    return FactoryProvider()


def test_dependency_factory():
    o = object()

    def test(*args, **kwargs):
        return o, args, kwargs

    df = DependencyFactory(factory=test,
                           singleton=True,
                           takes_dependency_id=False)

    assert repr(test) in repr(df)
    assert (o, (1,), {'param': 'none'}) == df(1, param='none')


def test_register(provider: FactoryProvider):
    provider.register(Service, Service)

    dependency = provider.__antidote_provide__(Dependency(Service))
    assert isinstance(dependency.item, Service)
    assert repr(Service) in repr(provider)


def test_register_factory_id(provider: FactoryProvider):
    provider.register(Service, lambda: Service())

    dependency = provider.__antidote_provide__(Dependency(Service))
    assert isinstance(dependency.item, Service)


def test_singleton(provider: FactoryProvider):
    provider.register(Service, Service, singleton=True)
    provider.register(AnotherService, AnotherService, singleton=False)

    provide = provider.__antidote_provide__
    assert provide(Dependency(Service)).singleton is True
    assert provide(Dependency(AnotherService)).singleton is False


def test_build_subclasses(provider: FactoryProvider):
    provider.register(Service, lambda cls: cls(), build_subclasses=True)

    assert isinstance(
        provider.__antidote_provide__(Dependency(Service)).item,
        Service
    )
    assert isinstance(
        provider.__antidote_provide__(Dependency(ServiceSubclass)).item,
        Service
    )

    with pytest.raises(DependencyNotProvidableError):
        provider.__antidote_provide__(Dependency(AnotherService))


def test_build_dependency(provider: FactoryProvider):
    provider.register(Service, Service)

    s = provider.__antidote_provide__(Build(Service, 1, val=object)).item
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

    with pytest.raises(DependencyDuplicateError):
        provider.register(Service, Service)

    with pytest.raises(DependencyDuplicateError):
        provider.register(Service, lambda: Service())
