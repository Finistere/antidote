import pytest

from antidote import register, world
from antidote.core import DependencyContainer
from antidote.providers import FactoryProvider, TagProvider


@pytest.fixture(autouse=True)
def test_world():
    with world.test.new():
        c = world.get(DependencyContainer)
        c.register_provider(FactoryProvider())
        c.register_provider(TagProvider())
        yield


def test_simple():
    @register
    class Service:
        pass

    assert isinstance(world.get(Service), Service)
    # singleton by default
    assert world.get(Service) is world.get(Service)


def test_singleton():
    @register(singleton=True)
    class Singleton:
        pass

    assert world.get(Singleton) is world.get(Singleton)

    @register(singleton=False)
    class NoScope:
        pass

    assert world.get(NoScope) != world.get(NoScope)


@pytest.mark.parametrize(
    'factory',
    [
        lambda cls: cls(),
        'class_build',
        'static_build',
        None
    ]
)
def test_factory(factory):
    @register(factory=factory)
    class Service:
        @classmethod
        def class_build(cls):
            return cls()

        @staticmethod
        def static_build(cls):
            return cls()

    assert isinstance(world.get(Service), Service)

    @register(factory=factory)
    class SubService(Service):
        pass

    assert isinstance(world.get(SubService), SubService)


def test_factory_dependency():
    @register(factory_dependency='factory')
    class Service:
        pass

    world.singletons.update(dict(factory=lambda cls: dict(service=cls())))
    assert isinstance(world.get(Service), dict)
    assert isinstance(world.get(Service)['service'], Service)


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


def test_not_tags():
    with world.test.empty():
        world.get(DependencyContainer).register_provider(FactoryProvider())

        @register
        class Service:
            pass

        assert isinstance(world.get(Service), Service)
        assert world.get(Service) is world.get(Service)

    with world.test.empty():
        world.get(DependencyContainer).register_provider(FactoryProvider())

        with pytest.raises(RuntimeError):
            @register(tags=['tag'])
            class Service:
                pass


