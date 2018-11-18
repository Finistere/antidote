import pytest

from antidote import (DependencyContainer, DependencyNotFoundError)
from antidote.container.proxy import ProxyContainer
from .utils import DummyProvider


class Service:
    def __init__(self, *args):
        pass


class AnotherService:
    def __init__(self, *args):
        pass


def test_invalid_arguments():
    with pytest.raises(ValueError):
        ProxyContainer(DependencyContainer(), include=object())

    with pytest.raises(ValueError):
        ProxyContainer(DependencyContainer(), exclude=object())

    with pytest.raises(ValueError):
        ProxyContainer(DependencyContainer(), missing=object())

    with pytest.raises(ValueError):
        ProxyContainer(DependencyContainer(), dependencies=object())


def test_context_isolation():
    container = DependencyContainer()
    container['test'] = 1
    container['name'] = 'Antidote'
    s = Service()
    container[Service] = s

    proxy_container = ProxyContainer(container)

    assert s is proxy_container[Service]
    assert 1 == proxy_container['test']
    assert 'Antidote' == proxy_container['name']

    proxy_container['another_service'] = AnotherService()
    assert isinstance(proxy_container['another_service'], AnotherService)

    s2 = Service()
    proxy_container[Service] = s2
    assert s2 is proxy_container[Service]

    with pytest.raises(DependencyNotFoundError):
        container['another_service']

    assert s is container[Service]
    assert 1 == container['test']
    assert 'Antidote' == container['name']


def test_context_include():
    container = DependencyContainer()
    container['test'] = 1
    container['name'] = 'Antidote'
    s = Service()
    container[Service] = s

    proxy_container = ProxyContainer(container, include=[Service])

    assert s is proxy_container[Service]

    with pytest.raises(DependencyNotFoundError):
        proxy_container['name']

    with pytest.raises(DependencyNotFoundError):
        proxy_container['test']

    proxy_container = ProxyContainer(container, include=[])

    with pytest.raises(DependencyNotFoundError):
        proxy_container[Service]

    with pytest.raises(DependencyNotFoundError):
        proxy_container['name']

    with pytest.raises(DependencyNotFoundError):
        proxy_container['test']


def test_context_exclude():
    container = DependencyContainer()
    container['test'] = 1
    container['name'] = 'Antidote'
    s = Service()
    container[Service] = s

    proxy_container = ProxyContainer(container, exclude=['name', 'unknown'])

    assert s is proxy_container[Service]
    assert 1 == proxy_container['test']

    with pytest.raises(DependencyNotFoundError):
        proxy_container['name']


def test_context_override():
    container = DependencyContainer()
    container['test'] = 1
    container['name'] = 'Antidote'
    s = Service()
    container[Service] = s

    proxy_container = ProxyContainer(container,
                                     dependencies=dict(test=2, name='testing'))

    assert s is proxy_container[Service]
    assert 2 == proxy_container['test']
    assert 'testing' == proxy_container['name']


def test_context_missing():
    container = DependencyContainer()
    container['test'] = 1
    container.providers[DummyProvider] = DummyProvider({'name': 'Antidote'})
    s = Service()
    container[Service] = s

    proxy_container = ProxyContainer(container, missing=['name'])

    assert s is proxy_container[Service]
    assert 1 == proxy_container['test']

    with pytest.raises(DependencyNotFoundError):
        proxy_container['name']

    proxy_container = ProxyContainer(container, missing=['test'], include=[Service])

    assert s is proxy_container[Service]
    assert 'Antidote' == proxy_container['name']

    with pytest.raises(DependencyNotFoundError):
        proxy_container['test']
