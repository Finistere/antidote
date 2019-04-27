import pytest

from antidote import register
from antidote.core import DependencyContainer
from antidote.providers.service import LazyFactory
from antidote.providers import ServiceProvider, TagProvider


@pytest.fixture()
def container():
    container = DependencyContainer()
    container.register_provider(ServiceProvider(container=container))
    container.register_provider(TagProvider(container=container))
    container.update_singletons({'instantiate': lambda cls: cls()})

    return container


def test_simple(container):
    @register(container=container)
    class Service:
        pass

    assert isinstance(container.get(Service), Service)
    # singleton by default
    assert container.get(Service) is container.get(Service)


def test_singleton(container):
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
        LazyFactory('instantiate'),
        None
    ]
)
def test_factory(container, factory):
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


@pytest.mark.parametrize('cls', ['test', object(), lambda: None])
def test_invalid_class(cls):
    with pytest.raises(TypeError):
        register(cls)


@pytest.mark.parametrize(
    'kwargs',
    [
        dict(factory=object()),
        dict(auto_wire=object()),
    ]
)
def test_invalid_params(kwargs):
    with pytest.raises(TypeError):
        @register(**kwargs)
        class Dummy:
            pass


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
