from dataclasses import dataclass
from typing import Dict, Iterator, Tuple

import pytest

from antidote import inject, lazy, world
from antidote.lib.lazy import register_lazy_provider


@pytest.fixture(autouse=True)
def setup_tests() -> Iterator[None]:
    with world.test.empty():
        register_lazy_provider()
        yield


@dataclass
class Dummy:
    name: str


@dataclass
class Bag:
    args: Tuple[object, ...]
    kwargs: Dict[str, object]

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.args = args
        self.kwargs = kwargs


def test_default() -> None:
    @lazy
    def dummy() -> Dummy:
        return Dummy(name="test")

    assert isinstance(dummy.call(), Dummy)

    @inject
    def f(x: Dummy = dummy()) -> Dummy:
        return x

    assert isinstance(f(), Dummy)
    assert f().name == "test"
    # singleton by default
    assert f() is f()

    d = world.get[Dummy](dummy())
    assert d is f()
    assert d is world.get[Dummy](dummy())


def test_single_arg() -> None:
    @lazy
    def named(name: str) -> Dummy:
        return Dummy(name=name)

    assert isinstance(named.call("test"), Dummy)
    assert named.call(name="test").name == "test"

    @inject
    def f(x: Dummy = named(name="f")) -> Dummy:
        return x

    @inject
    def g(x: Dummy = named("g")) -> Dummy:
        return x

    assert isinstance(f(), Dummy)
    assert f().name == "f"
    # singleton by default
    assert f() is world.get[Dummy](named(name="f"))
    assert f() is world.get[Dummy](named("f"))

    assert isinstance(g(), Dummy)
    assert f() is not g()
    assert g().name == "g"
    assert g() is world.get[Dummy](named(name="g"))


def test_not_singleton() -> None:
    @lazy(singleton=False)
    def dummy() -> Dummy:
        return Dummy(name="test")

    assert isinstance(dummy.call(), Dummy)

    @inject
    def f(x: Dummy = dummy()) -> Dummy:
        return x

    assert isinstance(f(), Dummy)
    assert f().name == "test"
    assert f() is not f()
    assert world.get[Dummy](dummy()) is not world.get[Dummy](dummy())
    assert world.get[Dummy](dummy()).name == "test"


def test_scope() -> None:
    scope = world.scopes.new(name="test")

    @lazy(scope=scope)
    def dummy() -> Dummy:
        return Dummy(name="test")

    @inject
    def f(x: Dummy = dummy()) -> Dummy:
        return x

    d = f()
    assert d is f()
    assert d is world.get[Dummy](dummy())

    world.scopes.reset(scope)
    d2 = f()
    assert d is not d2
    assert d2 is f()
    assert d2 is world.get[Dummy](dummy())


def test_not_singleton_with_arg() -> None:
    @lazy(singleton=False)
    def named(name: str) -> Dummy:
        return Dummy(name=name)

    @inject
    def f(x: Dummy = named("test")) -> Dummy:
        return x

    assert isinstance(f(), Dummy)
    assert f().name == "test"
    assert f() is not f()
    assert world.get[Dummy](named(name="test")) is not world.get[Dummy](named("test"))
    assert world.get[Dummy](named("test")).name == "test"


@pytest.mark.parametrize(
    "x", [Bag(a=[], b={}), Bag([], {}), Bag([], b={}), Bag(1, 2, 3, {}), Bag(a=1, b=2, c=3, d={})]
)
def test_unhashable_arguments(x: Bag) -> None:
    @lazy
    def bag(*args: object, **kwargs: object) -> Bag:
        ...

    with pytest.raises(TypeError):
        world.get[Bag](bag(*x.args, **x.kwargs))


@pytest.mark.parametrize("x", [Bag(a="test", b=(1, 2)), Bag("test", (1, 2)), Bag("test", b=(1, 2))])
def test_complex_arguments(x: Bag) -> None:
    @lazy
    def bag(*args: object, **kwargs: object) -> Bag:
        return Bag(*args, **kwargs)

    out = world.get[Bag](bag(*x.args, **x.kwargs))
    assert out == x
    assert out is world.get[Bag](bag(*x.args, **x.kwargs))


def test_equivalent_arguments() -> None:
    @lazy
    def f(a: str, b: int) -> Bag:
        ...

    dep = f("x", 0)
    assert dep is f(a="x", b=0)
    assert dep is f("x", b=0)
    assert dep is f("x", 0)


def test_invalid_function() -> None:
    with pytest.raises(TypeError, match="function"):
        lazy(object())  # type: ignore


def test_injected() -> None:
    @lazy
    def dummy() -> Dummy:
        return Dummy(name="dummy")

    @lazy
    def bag_of_dummy(d: Dummy = dummy()) -> Bag:
        return Bag(dummy=d)

    @inject
    def f(bag: Bag = bag_of_dummy()) -> Bag:
        return bag

    assert f() == Bag(dummy=Dummy(name="dummy"))

    @lazy
    @inject({"d": dummy()})
    def injected_bag(d: Dummy) -> Bag:
        return Bag(dummy=d)

    @inject
    def f2(bag: Bag = injected_bag()) -> Bag:
        return bag

    assert f2() == Bag(dummy=Dummy(name="dummy"))
