from typing import Callable

import pytest

from antidote import From, FromArg, Get, Service, world
from antidote._compatibility.typing import Annotated
from antidote._providers import ServiceProvider
from antidote.core import (Dependency)
from antidote.exceptions import DependencyNotFoundError, FrozenWorldError
from .utils import DummyIntProvider


@pytest.fixture(autouse=True)
def empty_world():
    with world.test.empty():
        yield


class A:
    pass


def test_get():
    world.provider(ServiceProvider)
    a = A()
    world.test.singleton(A, a)
    assert world.get(A) is a

    with pytest.raises(DependencyNotFoundError):
        world.get("nothing")

    class B(Service):
        pass

    assert world.get[A](A) is a
    assert world.get[B]() is world.get(B)


@pytest.mark.parametrize('getter', [
    pytest.param(world.get, id='get'),
    pytest.param(world.get[A], id='get[A]'),
    pytest.param(lambda x: world.lazy(x).get(), id='lazy'),
    pytest.param(lambda x: world.lazy[A](x).get(), id='lazy[A]')
])
def test_annotation_support(getter: Callable[[object], object]):
    class Maker:
        def __rmatmul__(self, other):
            return 'maker'

    world.test.singleton({
        A: A(),
        'a': A(),
        'maker': A()
    })
    assert getter(Annotated[A, object()]) is world.get(A)
    assert getter(Annotated[A, Get('a')]) is world.get('a')  # noqa: F821
    assert getter(Annotated[A, From(Maker())]) is world.get('maker')

    with pytest.raises(TypeError):
        getter(Annotated[A, Get('a'), Get('a')])  # noqa: F821

    with pytest.raises(TypeError):
        getter(Annotated[A, FromArg(lambda a: a)])  # noqa: F821


@pytest.mark.parametrize('getter', [
    pytest.param(lambda x, d: world.get(x, default=d), id='get'),
    pytest.param(lambda x, d: world.get[A](x, default=d), id='get[A]')
])
def test_default(getter: Callable[[object, object], object]):
    world.test.singleton(A, A())
    assert getter(A, 'default') is world.get(A)
    assert getter('a', 'default') == 'default'


def test_lazy():
    world.test.singleton({
        'x': object(),
        A: A()
    })

    lazy = world.lazy('x')
    assert isinstance(lazy, Dependency)
    assert lazy.unwrapped == 'x'
    assert lazy.get() == world.get('x')

    lazy = world.lazy[int]('x')
    assert isinstance(lazy, Dependency)
    assert lazy.unwrapped == 'x'
    assert lazy.get() == world.get('x')
    assert world.lazy[A]().get() is world.get(A)


def test_freeze():
    world.provider(ServiceProvider)
    factory = world.get(ServiceProvider)

    class Service:
        pass

    world.freeze()
    with pytest.raises(FrozenWorldError):
        world.test.singleton("test", "x")

    with pytest.raises(FrozenWorldError):
        factory.register(Service, scope=None)


def test_add_provider():
    world.provider(DummyIntProvider)
    assert world.get(10) == 20


def test_no_duplicate_provider():
    world.provider(DummyIntProvider)
    assert world.get(10) == 20

    with pytest.raises(ValueError, match=".*already exists.*"):
        world.provider(DummyIntProvider)


@pytest.mark.parametrize('p, expectation', [
    (object(), pytest.raises(TypeError, match=".*RawProvider.*")),
    (A, pytest.raises(TypeError, match=".*RawProvider.*"))
])
def test_invalid_add_provider(p, expectation):
    with expectation:
        world.provider(p)
