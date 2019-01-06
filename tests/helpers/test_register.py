import pytest

from antidote import register
from antidote.core import DependencyContainer, Lazy
from antidote.providers import ServiceProvider, TagProvider


@pytest.fixture()
def container():
    c = DependencyContainer()
    c.register_provider(ServiceProvider(container=c))
    c.register_provider(TagProvider(container=c))
    c['instantiate'] = lambda cls: cls()

    return c


def test_simple(container):
    @register(container=container)
    class Service:
        pass

    assert isinstance(container[Service], Service)
    # singleton by default
    assert container[Service] is container[Service]


def test_singleton(container):
    @register(container=container, singleton=True)
    class Singleton:
        pass

    assert container[Singleton] is container[Singleton]

    @register(container=container, singleton=False)
    class NoScope:
        pass

    assert container[NoScope] != container[NoScope]


@pytest.mark.parametrize(
    'factory',
    [
        lambda cls: cls(),
        'class_build',
        'static_build',
        Lazy('instantiate'),
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

    assert isinstance(container[Service], Service)

    @register(container=container, factory=factory)
    class SubService(Service):
        pass

    assert isinstance(container[SubService], SubService)


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
        @register(factory='build', use_mro=False)
        class Dummy2(NewDummy):
            pass
