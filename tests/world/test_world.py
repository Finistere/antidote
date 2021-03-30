from typing import Callable

import pytest

from antidote import From, FromArg, Get, Service, factory, world
from antidote._compatibility.typing import Annotated
from antidote._internal.world import LazyDependency
from antidote._providers import FactoryProvider, ServiceProvider
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

    class B(Service):
        pass

    assert world.get[A](A) is a
    assert world.get[B]() is world.get(B)

    b = B()
    assert world.get(B, default=b) is world.get(B)
    assert world.get[B](default=b) is world.get(B)

    with pytest.raises(DependencyNotFoundError):
        world.get(Service)

    with pytest.raises(DependencyNotFoundError):
        world.get[Service]()

    assert world.get[Service](default=b) is b


def test_get_type_safety():
    x = object()
    world.test.singleton(A, x)

    assert world.get(A) is x  # without type hints, it should not fail
    with pytest.raises(TypeError):
        world.get[A]()

    class B:
        pass

    assert world.get(B, default=x) is x
    with pytest.raises(TypeError, match=".*default.*"):
        world.get[B](default=x)


def test_get_factory():
    world.provider(FactoryProvider)

    @factory
    def build_a() -> A:
        return A()

    assert world.get[A] @ build_a is world.get(A @ build_a)


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


def test_lazy():
    world.test.singleton({
        'x': object(),
        A: A()
    })

    lazy = world.lazy('x')
    assert isinstance(lazy, LazyDependency)
    assert lazy.unwrapped == 'x'
    assert lazy.get() == world.get('x')

    lazy = world.lazy[A](A)
    assert isinstance(lazy, LazyDependency)
    assert lazy.unwrapped == A
    assert lazy.get() == world.get(A)

    assert world.lazy[A]().get() is world.get(A)


def test_lazy_type_safety():
    x = object()
    world.test.singleton(A, x)

    assert world.lazy(A).get() is x

    with pytest.raises(TypeError):
        world.lazy[A]().get()


def test_lazy_factory():
    world.provider(FactoryProvider)

    @factory
    def build_a() -> A:
        return A()

    assert (world.lazy[A] @ build_a).get() is world.get(A @ build_a)


def test_freeze():
    world.provider(ServiceProvider)
    provider = world.get[ServiceProvider]()

    class Service:
        pass

    world.freeze()
    with pytest.raises(FrozenWorldError):
        world.test.singleton("test", "x")

    with pytest.raises(FrozenWorldError):
        provider.register(Service, scope=None)


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
