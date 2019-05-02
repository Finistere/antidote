import pytest

from antidote import factory
from antidote.core import DependencyContainer
from antidote.providers import FactoryProvider, TagProvider


@pytest.fixture()
def container():
    c = DependencyContainer()
    c.register_provider(FactoryProvider(container=c))
    c.register_provider(TagProvider(container=c))

    return c


class Service:
    pass


class AnotherService:
    pass


class YetAnotherService:
    pass


class SuperService:
    pass


def test_function(container):
    @factory(container=container)
    def build() -> Service:
        return Service()

    assert isinstance(container.get(Service), Service)
    # singleton by default
    assert container.get(Service) is container.get(Service)


def test_class(container):
    @factory(container=container)
    class ServiceFactory:
        def __call__(self) -> Service:
            return Service()

    assert isinstance(container.get(Service), Service)
    # singleton by default
    assert container.get(Service) is container.get(Service)


def test_missing_return_type_hint(container):
    with pytest.raises(ValueError):
        @factory(container=container)
        def faulty_service_provider():
            return Service()

    with pytest.raises(ValueError):
        @factory(container=container)
        class FaultyServiceFactory:
            def __call__(self):
                return Service()


@pytest.mark.parametrize('func', [1, type('MissingCall', tuple(), {})])
def test_invalid_func(func):
    with pytest.raises(TypeError):
        factory(func)
