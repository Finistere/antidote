import pytest

from antidote.core import Lazy, DependencyContainer
from antidote.exceptions import DuplicateDependencyError
from antidote.providers.service import Build, ServiceProvider


class Service:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class AnotherService:
    def __init__(self, *args):
        pass


@pytest.fixture()
def provider():
    container = DependencyContainer()
    provider = ServiceProvider(container=container)
    container.register_provider(provider)
    return provider


@pytest.mark.parametrize(
    'wrapped,args,kwargs',
    [
        ('test', (1,), {}),
        (1, tuple(), {'test': 1}),
        (Service, (1, 'test'), {'another': 'no'}),
        (Service, tuple(), {'not_hashable': {'hey': 'hey'}})
    ]
)
def test_build_eq_hash(wrapped, args, kwargs):
    b = Build(wrapped, *args, **kwargs)

    # does not fail
    hash(b)

    for f in (lambda e: e, hash):
        assert f(Build(wrapped, *args, **kwargs)) == f(b)

    assert repr(wrapped) in repr(b)
    if args or kwargs:
        assert repr(args) in repr(b)
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


def test_simple(provider: ServiceProvider):
    provider.register(factory=Service, service=Service)

    dependency = provider.provide(Service)
    assert isinstance(dependency.instance, Service)
    assert repr(Service) in repr(provider)


def test_singleton(provider: ServiceProvider):
    provider.register(factory=Service, service=Service, singleton=True)
    provider.register(factory=AnotherService, service=AnotherService,
                      singleton=False)

    provide = provider.provide
    assert provide(Service).singleton is True
    assert provide(AnotherService).singleton is False


def test_takes_dependency(provider: ServiceProvider):
    provider.register(factory=lambda cls: cls(), service=Service,
                      takes_dependency=True)

    assert isinstance(provider.provide(Service).instance, Service)
    assert provider.provide(AnotherService) is None


def test_build(provider: ServiceProvider):
    provider.register(factory=Service, service=Service)

    s = provider.provide(Build(Service, 1, val=object)).instance
    assert isinstance(s, Service)
    assert (1,) == s.args
    assert dict(val=object) == s.kwargs


def test_lazy(provider: ServiceProvider):
    sentinel = object()
    provider._container['lazy_getter'] = lambda: sentinel
    provider.register(factory=Lazy('lazy_getter'), service=Service)

    assert sentinel is provider.provide(Service).instance


def test_duplicate_error(provider: ServiceProvider):
    provider.register(factory=Service, service=Service)

    with pytest.raises(DuplicateDependencyError):
        provider.register(factory=Service, service=Service)

    with pytest.raises(DuplicateDependencyError):
        provider.register(factory=lambda: Service(), service=Service)


@pytest.mark.parametrize('factory', ['test', object()])
def test_invalid_factory(provider: ServiceProvider, factory):
    with pytest.raises(ValueError):
        provider.register(factory=factory, service=Service)


@pytest.mark.parametrize('service', ['test', object()])
def test_invalid_service(provider: ServiceProvider, service):
    with pytest.raises(TypeError):
        provider.register(service=service)


@pytest.mark.parametrize('dependency', ['test', Service, object()])
def test_unknown_dependency(provider: ServiceProvider, dependency):
    assert provider.provide(dependency) is None

