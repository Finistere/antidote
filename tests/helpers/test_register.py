import pytest

from antidote import (DependencyContainer, FactoryProvider, TagProvider)
from antidote.helpers import register


@pytest.fixture()
def container():
    c = DependencyContainer()
    c.register_provider(FactoryProvider())
    c.register_provider(TagProvider(container=c))

    return c


def test_simple(container):
    @register(container=container)
    class Service:
        pass

    assert isinstance(container[Service], Service)
    # singleton by default
    assert container[Service] is container[Service]


def test_invalid_register(container):
    with pytest.raises(ValueError):
        register(object())

    def f():
        pass

    with pytest.raises(ValueError):
        register(f)
