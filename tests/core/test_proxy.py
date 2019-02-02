import pytest

from antidote.core import DependencyContainer, ProxyContainer
from antidote.exceptions import DependencyNotFoundError
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
    container.update_singletons({'test': 1})
    container.update_singletons({'name': 'Antidote'})
    s = Service()
    container.update_singletons({Service: s})

    proxy_container = ProxyContainer(container)

    assert s is proxy_container.get(Service)
    assert 1 == proxy_container.get('test')
    assert 'Antidote' == proxy_container.get('name')

    proxy_container.update_singletons({'another_service': AnotherService()})
    assert isinstance(proxy_container.get('another_service'), AnotherService)

    s2 = Service()
    proxy_container.update_singletons({Service: s2})
    assert s2 is proxy_container.get(Service)

    with pytest.raises(DependencyNotFoundError):
        container.get('another_service')

    assert s is container.get(Service)
    assert 1 == container.get('test')
    assert 'Antidote' == container.get('name')


def test_context_include():
    container = DependencyContainer()
    container.update_singletons({'test': 1})
    container.update_singletons({'name': 'Antidote'})
    s = Service()
    container.update_singletons({Service: s})

    proxy_container = ProxyContainer(container, include=[Service])

    assert s is proxy_container.get(Service)

    with pytest.raises(DependencyNotFoundError):
        proxy_container.get('name')

    with pytest.raises(DependencyNotFoundError):
        proxy_container.get('test')

    proxy_container = ProxyContainer(container, include=[])

    with pytest.raises(DependencyNotFoundError):
        proxy_container.get(Service)

    with pytest.raises(DependencyNotFoundError):
        proxy_container.get('name')

    with pytest.raises(DependencyNotFoundError):
        proxy_container.get('test')


def test_context_exclude():
    container = DependencyContainer()
    container.update_singletons({'test': 1})
    container.update_singletons({'name': 'Antidote'})
    s = Service()
    container.update_singletons({Service: s})

    proxy_container = ProxyContainer(container, exclude=['name', 'unknown'])

    assert s is proxy_container.get(Service)
    assert 1 == proxy_container.get('test')

    with pytest.raises(DependencyNotFoundError):
        proxy_container.get('name')


def test_context_override():
    container = DependencyContainer()
    container.update_singletons({'test': 1})
    container.update_singletons({'name': 'Antidote'})
    s = Service()
    container.update_singletons({Service: s})

    proxy_container = ProxyContainer(container,
                                     dependencies=dict(test=2, name='testing'))

    assert s is proxy_container.get(Service)
    assert 2 == proxy_container.get('test')
    assert 'testing' == proxy_container.get('name')


def test_context_missing():
    container = DependencyContainer()
    container.update_singletons({'test': 1})
    container.register_provider(DummyProvider({'name': 'Antidote'}))
    s = Service()
    container.update_singletons({Service: s})

    proxy_container = ProxyContainer(container, missing=['name'])

    assert s is proxy_container.get(Service)
    assert 1 == proxy_container.get('test')

    with pytest.raises(DependencyNotFoundError):
        proxy_container.get('name')

    proxy_container = ProxyContainer(container, missing=['test'], include=[Service])

    assert s is proxy_container.get(Service)
    assert 'Antidote' == proxy_container.get('name')

    with pytest.raises(DependencyNotFoundError):
        proxy_container.get('test')
