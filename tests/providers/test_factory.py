import pytest

from antidote.core import DependencyContainer
from antidote.exceptions import DuplicateDependencyError
from antidote.providers.factory import Build, FactoryProvider


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
    provider = FactoryProvider(container=container)
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


def test_simple(provider: FactoryProvider):
    provider.register_class(Service)

    dependency = provider.provide(Service)
    assert isinstance(dependency.instance, Service)
    assert repr(Service) in repr(provider)


def test_singleton(provider: FactoryProvider):
    provider.register_class(Service, singleton=True)
    provider.register_class(AnotherService, singleton=False)

    provide = provider.provide
    assert provide(Service).singleton is True
    assert provide(AnotherService).singleton is False


def test_takes_dependency(provider: FactoryProvider):
    provider.register_factory(factory=lambda cls: cls(), dependency=Service,
                              takes_dependency=True)

    assert isinstance(provider.provide(Service).instance, Service)
    assert provider.provide(AnotherService) is None


def test_build(provider: FactoryProvider):
    provider.register_class(Service)

    s = provider.provide(Build(Service, 1, val=object)).instance
    assert isinstance(s, Service)
    assert (1,) == s.args
    assert dict(val=object) == s.kwargs
#
#
# def test_lazy(provider: FactoryProvider):
#     sentinel = object()
#     provider._container.update_singletons({
#         'lazy_getter': lambda: sentinel
#     })
#     provider.register_factory(factory=LazyFactory('lazy_getter'), dependency=Service)
#
#     assert sentinel is provider.provide(Service).instance


def test_duplicate_error(provider: FactoryProvider):
    provider.register_class(Service)

    with pytest.raises(DuplicateDependencyError):
        provider.register_class(Service)

    with pytest.raises(DuplicateDependencyError):
        provider.register_factory(factory=lambda: Service(), dependency=Service)


@pytest.mark.parametrize(
    'kwargs',
    [dict(service='test'),
     dict(service=object()),
     dict(factory='test', service=Service),
     dict(factory=object(), service=Service)]
)
def test_invalid_type(provider: FactoryProvider, kwargs):
    with pytest.raises(TypeError):
        provider.register_factory(**kwargs)


@pytest.mark.parametrize('dependency', ['test', Service, object()])
def test_unknown_dependency(provider: FactoryProvider, dependency):
    assert provider.provide(dependency) is None
