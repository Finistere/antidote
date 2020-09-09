import pytest

from antidote import world
from antidote.core import DependencyContainer
from antidote.core.exceptions import DependencyNotFoundError, FrozenWorldError
from antidote.providers import FactoryProvider


@pytest.fixture(autouse=True)
def empty_world():
    with world.test.empty():
        yield


def test_singletons():
    world.singletons.set("singleton", 12342)
    assert 12342 == world.get("singleton")

    world.singletons.update({
        "singleton": 89,
        "singleton2": 123
    })
    assert world.get("singleton") == 89
    assert world.get("singleton2") == 123


def test_get():
    world.singletons.set("singleton", 1)
    assert 1 == world.get("singleton")

    with pytest.raises(DependencyNotFoundError):
        world.get("nothing")


def test_local():
    world.singletons.set("singleton", 2)

    with world.test.clone(keep_singletons=True):
        world.singletons.set("a", 3)
        assert 2 == world.get("singleton")
        assert 3 == world.get("a")

    with world.test.clone(keep_singletons=False):
        world.singletons.set("a", 3)
        assert 3 == world.get("a")
        with pytest.raises(DependencyNotFoundError):
            world.get("singleton")

    with pytest.raises(DependencyNotFoundError):
        world.get("a")

    with world.test.empty():
        world.singletons.set("a", 4)
        assert 4 == world.get("a")
        with pytest.raises(DependencyNotFoundError):
            world.get("singleton")


def test_freeze():
    factory = FactoryProvider()
    world.get(DependencyContainer).register_provider(factory)

    class Service:
        pass

    world.freeze()
    with pytest.raises(FrozenWorldError):
        world.singletons.set("test", "x")

    with pytest.raises(FrozenWorldError):
        factory.register_class(Service)
