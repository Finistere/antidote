import pytest

from antidote import Get, auto_inject, world
from antidote._compatibility.typing import Annotated


def test_invalid():
    with pytest.raises(TypeError, match=".*function.*"):
        auto_inject()(object())

    with pytest.raises(ValueError, match="(?i).*either.*positional.*named.*"):
        auto_inject(1, y=2)


class Service:
    pass


@pytest.fixture(autouse=True)
def current_world():
    with world.test.empty():
        world.test.singleton(Service, Service())
        yield


def test_function():
    @auto_inject()
    def f(x: Service):
        return x

    @auto_inject()
    def g(z: Annotated[object, Get(Service)]):
        return z

    @auto_inject()
    def h(y):
        return y

    assert f() is world.get(Service)
    assert g() is world.get(Service)

    with pytest.raises(TypeError):
        h()


def test_positional_dependencies():
    sentinel = object()

    @auto_inject(Service)
    def f(y):
        return y

    assert f() is world.get(Service)

    @auto_inject(None, Service)
    def g(x=sentinel, y=sentinel):
        assert x is sentinel
        return y

    assert g() is world.get(Service)


def test_named_dependencies():
    sentinel = object()

    @auto_inject(y=Service)
    def f(y):
        return y

    assert f() is world.get(Service)

    @auto_inject(y=Service)
    def g(x=sentinel, y=sentinel):
        assert x is sentinel
        return y

    assert g() is world.get(Service)
