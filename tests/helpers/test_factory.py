import pytest

from antidote import factory, world
from antidote.core import DependencyContainer
from antidote.providers import FactoryProvider, TagProvider
from antidote.providers.factory import Factory


@pytest.fixture(autouse=True)
def test_world():
    with world.test.new():
        c = world.get(DependencyContainer)
        c.register_provider(FactoryProvider())
        c.register_provider(TagProvider())
        yield


class Service:
    pass


class AnotherService:
    pass


class YetAnotherService:
    pass


class SuperService:
    pass


def test_function():
    @factory
    def build() -> Service:
        return Service()

    assert isinstance(world.get(Service @ build), Service)
    # singleton by default
    assert world.get(Service) is world.get(Service)


def test_class():
    @factory
    class ServiceFactory:
        def __call__(self) -> Service:
            return Service()

    assert isinstance(world.get(Service @ ServiceFactory), Service)
    # singleton by default
    assert world.get(Service) is world.get(Service)


def test_missing_return_type_hint():
    with pytest.raises(ValueError):
        @factory
        def faulty_service_provider():
            return Service()

    with pytest.raises(ValueError):
        @factory
        class FaultyServiceFactory:
            def __call__(self):
                return Service()


@pytest.mark.parametrize('func', [1, type('MissingCall', tuple(), {})])
def test_invalid_func(func):
    with pytest.raises(TypeError):
        factory(func)


def test_not_tags():
    with world.test.empty():
        world.get(DependencyContainer).register_provider(FactoryProvider())

        @factory
        def build() -> Service:
            return Service()

        assert isinstance(world.get(Service), Service)
        assert world.get(Service) is world.get(Service)

    with world.test.empty():
        world.get(DependencyContainer).register_provider(FactoryProvider())

        with pytest.raises(RuntimeError):
            @factory(tags=['tag'])
            def build() -> Service:
                return Service()
