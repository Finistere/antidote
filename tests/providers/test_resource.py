import pytest

from antidote.core import DependencyInstance, Lazy, DependencyContainer
from antidote.exceptions import ResourcePriorityConflict
from antidote.providers import ResourceProvider


@pytest.fixture()
def provider():
    container = DependencyContainer()
    provider = ResourceProvider(container=container)
    container.register_provider(provider)
    return provider


def test_repr(provider: ResourceProvider):
    def getter(_):
        pass

    provider.register(getter=getter, namespace='a')

    assert str(getter) in repr(provider)


def test_simple(provider: ResourceProvider):
    data = dict(y=object(), x=object())

    def getter(key):
        return data[key]

    provider.register(getter=getter, namespace='a')

    assert isinstance(provider.provide('a:y'), DependencyInstance)
    assert data['y'] == provider.provide('a:y').instance
    assert data['x'] == provider.provide('a:x').instance

    assert provider.provide('a:z') is None


def test_namespace(provider: ResourceProvider):
    provider.register(getter=lambda _: 1, namespace='g1')
    provider.register(getter=lambda _: 2, namespace='g2')

    assert 1 == provider.provide('g1:test').instance
    assert 2 == provider.provide('g2:test').instance

    assert provider.provide('g3:test') is None


def test_priority(provider: ResourceProvider):
    def high(key):
        return {'test': 'high'}[key]

    def low(_):
        return 'low'

    provider.register(getter=high, namespace='g', priority=2)
    provider.register(getter=low, namespace='g', priority=-1)

    assert 'high' == provider.provide('g:test').instance
    assert 'low' == provider.provide('g:test2').instance


def test_priority_conflict(provider: ResourceProvider):
    provider.register(getter=lambda _: None, namespace='g', priority=2)

    with pytest.raises(ResourcePriorityConflict):
        provider.register(getter=lambda _: None, namespace='g', priority=2)


def test_singleton(provider: ResourceProvider):
    provider.register(lambda _: object(), namespace='default')
    assert True is provider.provide('default:').singleton


def test_lazy(provider: ResourceProvider):
    sentinel = object()
    provider._container['lazy_getter'] = lambda _: sentinel
    provider.register(Lazy('lazy_getter'), namespace='test')

    assert sentinel is provider.provide('test:dummy').instance


@pytest.mark.parametrize('namespace', ['test:', 'test ', 'Nop!yes', '', object(), 1])
def test_invalid_namespace(provider: ResourceProvider, namespace):
    with pytest.raises((TypeError,  # TypeError for Cython
                        ValueError)):  # TypeError for pure Python
        provider.register(getter=lambda _: None, namespace=namespace)


@pytest.mark.parametrize('priority', ['test', 1 + 3j, None])
def test_invalid_priority(provider: ResourceProvider, priority):
    with pytest.raises((TypeError,  # TypeError for Cython
                        ValueError)):  # TypeError for pure Python
        provider.register(getter=lambda _: None, namespace='test',
                          priority=priority)


@pytest.mark.parametrize('getter', ['test', object()])
def test_invalid_getter(provider: ResourceProvider, getter):
    with pytest.raises(ValueError):
        provider.register(getter, 'dummy')


@pytest.mark.parametrize('dependency', ['test', 'test:value', object()])
def test_unknown_dependency(provider: ResourceProvider, dependency):
    assert provider.provide(dependency) is None
