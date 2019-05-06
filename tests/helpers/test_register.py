from typing import cast

import pytest

from antidote import register
from antidote.core import DependencyContainer
from antidote.providers import FactoryProvider, TagProvider


@pytest.fixture()
def container():
    container = DependencyContainer()
    container.register_provider(FactoryProvider(container=container))
    container.register_provider(TagProvider(container=container))

    return container


def test_simple(container: DependencyContainer):
    @register(container=container)
    class Service:
        pass

    assert isinstance(container.get(Service), Service)
    # singleton by default
    assert container.get(Service) is container.get(Service)


def test_singleton(container: DependencyContainer):
    @register(container=container, singleton=True)
    class Singleton:
        pass

    assert container.get(Singleton) is container.get(Singleton)

    @register(container=container, singleton=False)
    class NoScope:
        pass

    assert container.get(NoScope) != container.get(NoScope)


@pytest.mark.parametrize(
    'factory',
    [
        lambda cls: cls(),
        'class_build',
        'static_build',
        None
    ]
)
def test_factory(container: DependencyContainer, factory):
    @register(container=container, factory=factory)
    class Service:
        @classmethod
        def class_build(cls):
            return cls()

        @staticmethod
        def static_build(cls):
            return cls()

    assert isinstance(container.get(Service), Service)

    @register(container=container, factory=factory)
    class SubService(Service):
        pass

    assert isinstance(container.get(SubService), SubService)


def test_factory_dependency(container: DependencyContainer):
    @register(container=container, factory_dependency='factory')
    class Service:
        pass

    container.update_singletons(dict(factory=lambda cls: dict(service=cls())))
    assert isinstance(container.get(Service), dict)
    assert isinstance(container.get(Service)['service'], Service)


@pytest.mark.parametrize('cls', ['test', object(), lambda: None])
def test_invalid_class(cls):
    with pytest.raises(TypeError):
        register(cls)


@pytest.mark.parametrize(
    'error,kwargs',
    [
        (TypeError, dict(factory=object())),
        (TypeError, dict(auto_wire=object())),
        (ValueError, dict(factory=lambda: None, factory_dependency=object())),
        (TypeError, dict(factory='method', auto_wire=False)),
    ]
)
def test_invalid_params(error, kwargs):
    with pytest.raises(error):
        @register(**kwargs)
        class Dummy:
            method = None


def test_invalid_factory_wiring():
    with pytest.raises(AttributeError):
        @register(factory='build')
        class Dummy:
            pass

    class NewDummy:
        @classmethod
        def build(cls):
            return cls()

    with pytest.raises(TypeError):
        @register(factory='build', wire_super=False)
        class Dummy2(NewDummy):
            pass
