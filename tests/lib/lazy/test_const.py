# pyright: reportUnusedFunction=false, reportUnusedClass=false
from __future__ import annotations

from enum import Enum
from typing import Any, Iterator, Tuple, TypeVar

import pytest

from antidote import antidote_injectable, const, Dependency, inject, injectable, new_catalog, world
from antidote.lib.lazy import antidote_lazy
from antidote.lib.lazy.constant import ConstFactory
from tests.utils import Box, expected_debug, Obj

T = TypeVar("T")

x = Obj()
y = Obj()


class Choice(Enum):
    YES = "YES"
    NO = "NO"


class Unknown:
    pass


@pytest.fixture(autouse=True)
def setup_tests(monkeypatch: Any) -> Iterator[None]:
    monkeypatch.setenv("HOST", "host")
    monkeypatch.setenv("PORT", "80")
    monkeypatch.setenv("CHOICE", "YES")
    monkeypatch.delenv("MISSING", raising=False)

    with world.test.empty():
        world.include(antidote_lazy)
        yield


def test_debug() -> None:
    world.include(antidote_injectable)

    @const.factory
    def fun(key: str) -> Box[str]:
        return Box(key)

    @injectable
    class Conf:
        @const.factory.method
        def method(self, key: str) -> Box[str]:
            return Box(key)

        @const.factory
        @staticmethod
        def static(key: str) -> Box[str]:
            return Box(key)

        C = method("C")

    class OtherConf:
        C = Conf.method("C")
        D = Conf.static("D")

    HOST: Dependency[Box[str]] = const.env(cast=Box)
    A = const("Hello world!")
    B = fun("B")
    C = Conf.method("C")
    D = Conf.static("D")

    line_number = 65
    namespace = "tests.lib.lazy.test_const.test_debug.<locals>"
    assert world.debug(HOST) == expected_debug(
        f"""
    🟉 <const> HOST@tests.lib.lazy.test_const:{line_number}
    """
    )
    assert world.debug(A) == expected_debug(
        """
    🟉 <const> 'Hello world!'
    """
    )
    assert world.debug(B) == expected_debug(
        f"""
    🟉 <const> B@tests.lib.lazy.test_const:{line_number + 2}
    """
    )
    assert world.debug(C) == expected_debug(
        f"""
    🟉 <const> C@tests.lib.lazy.test_const:{line_number + 3}
    └── 🟉 tests.lib.lazy.test_const.test_debug.<locals>.Conf
    """
    )
    assert world.debug(D) == expected_debug(
        f"""
    🟉 <const> D@tests.lib.lazy.test_const:{line_number + 4}
    """
    )
    assert world.debug(Conf.C) == expected_debug(
        f"""
    🟉 <const> {namespace}.Conf.C
    └── 🟉 tests.lib.lazy.test_const.test_debug.<locals>.Conf
    """
    )
    assert world.debug(OtherConf.C) == expected_debug(
        f"""
    🟉 <const> {namespace}.OtherConf.C
    └── 🟉 tests.lib.lazy.test_const.test_debug.<locals>.Conf
    """
    )
    assert world.debug(OtherConf.D) == expected_debug(
        f"""
    🟉 <const> {namespace}.OtherConf.D
    """
    )


def test_simple_const() -> None:
    catalog = new_catalog(include=[antidote_lazy])

    constant = const(x)
    # const may carry mutable objects, so they cannot be the same.
    assert constant != const(x)
    assert constant != const(y)
    assert constant != object()

    assert world[constant] is x
    assert constant not in catalog

    assert str(world.id) in repr(constant)
    assert repr(x) in world.debug(constant)
    assert repr(x) in repr(constant)

    dep2 = const(x, catalog=catalog)
    assert dep2 in catalog
    assert dep2 not in world

    with pytest.raises(TypeError, match="catalog_id"):
        const(x, catalog_id=object())  # type: ignore

    @inject
    def f(a: object = inject[constant]) -> object:
        return a

    assert f() is x


def test_simple_class_const() -> None:
    class Conf:
        HOST = const("host")
        PORT = const(80)

    assert world[Conf.HOST] == "host"
    assert world[Conf.PORT] == 80
    assert str(world.id) in repr(Conf.HOST)
    assert "host" in repr(Conf.HOST)
    assert "host" in world.debug(Conf.HOST)
    assert "80" in repr(Conf.PORT)
    assert "80" in world.debug(Conf.PORT)

    @inject
    def f(host: str = inject[Conf.HOST], port: int = inject[Conf.PORT]) -> Tuple[str, int]:
        return host, port

    assert f() == ("host", 80)

    conf = Conf()
    assert world[conf.HOST] == "host"
    assert world[conf.PORT] == 80


def test_env() -> None:
    HOST: Dependency[str] = const.env()
    PORT: Dependency[int] = const.env(cast=int)
    CHOICE: Dependency[Choice] = const.env(cast=Choice)
    MISSING: Dependency[int] = const.env(default=99)
    NOT_FOUND = const.env("MISSING")

    assert world[HOST] == "host"
    assert world[PORT] == 80
    assert world[CHOICE] == Choice.YES
    assert world[MISSING] == 99
    assert str(world.id) in repr(HOST)
    assert "HOST" in repr(HOST)
    assert "HOST" in world.debug(HOST)
    assert "MISSING" in repr(NOT_FOUND)
    assert "NOT_FOUND" in repr(NOT_FOUND)
    assert "NOT_FOUND" in world.debug(NOT_FOUND)

    class Conf:
        HOST: Dependency[str] = const.env()
        PORT: Dependency[int] = const.env(cast=int)
        CHOICE: Dependency[Choice] = const.env(cast=Choice)
        MISSING: Dependency[int] = const.env(default=99)
        NOT_FOUND = const.env("MISSING")

    assert world[Conf.HOST] == "host"
    assert world[Conf.PORT] == 80
    assert world[Conf.CHOICE] == Choice.YES
    assert world[Conf.MISSING] == 99
    assert "HOST" in repr(Conf.HOST)
    assert "HOST" in world.debug(Conf.HOST)
    assert "MISSING" in repr(Conf.NOT_FOUND)
    assert "NOT_FOUND" in repr(Conf.NOT_FOUND)
    assert "NOT_FOUND" in world.debug(Conf.NOT_FOUND)

    with pytest.raises(LookupError, match="MISSING"):
        _ = world[NOT_FOUND]

    const.env(default=90, cast=int)  # should not fail
    with pytest.raises(TypeError, match="default.*cast"):
        const.env(default=90, cast=str)

    with pytest.raises(TypeError, match="first argument"):
        const.env(object())  # type: ignore


def test_const_factory() -> None:
    @const.factory
    def square(a: int) -> int:
        return a**2

    BIG: Dependency[int] = square(12)
    SMALL: Dependency[int] = square(a=2)

    assert world[BIG] == 144
    assert world[SMALL] == 4
    assert str(world.id) in repr(SMALL)
    assert "SMALL" in repr(SMALL)
    assert "SMALL" in world.debug(SMALL)

    @const.factory
    def box_square(a: int) -> Box[int]:
        return Box(a**2)

    class Conf:
        FIRST: Dependency[Box[int]] = box_square(3)
        SECOND: Dependency[Box[int]] = box_square(3)

    first = world[Conf.FIRST]
    second = world[Conf.SECOND]
    assert first == Box(9)
    assert second == Box(9)
    assert first is not second
    assert world[Conf.FIRST] is first
    assert world[Conf.SECOND] is second
    assert str(world.id) in repr(Conf.FIRST)
    assert "FIRST" in repr(Conf.FIRST)
    assert "FIRST" in world.debug(Conf.FIRST)

    assert square.__wrapped__(7) == 49

    with pytest.raises(TypeError):
        square(1, 2)  # type: ignore

    with pytest.raises(TypeError):
        square(a=1, b=2)  # type: ignore


@pytest.mark.parametrize(
    "func",
    [
        pytest.param(const.factory, id="const.factory"),
        pytest.param(const.factory.method, id="const.factory.method"),
    ],
)
def test_invalid_factory(func: ConstFactory) -> None:
    with pytest.raises(TypeError, match="catalog"):
        func(catalog=object())  # type: ignore

    with pytest.raises(TypeError, match="inject"):
        func(inject=object())  # type: ignore

    with pytest.raises(TypeError, match="type_hints_locals"):
        func(type_hints_locals=object())  # type: ignore

    with pytest.raises(TypeError, match="function"):
        func(object())  # type: ignore


def test_duplicate_factory() -> None:
    with pytest.raises(TypeError, match="existing const factory"):

        @const.factory
        @const.factory
        def f() -> int:
            ...

    class Dummy:
        with pytest.raises(TypeError, match="existing const factory"):

            @const.factory.method  # type: ignore
            @const.factory.method
            def f(self) -> int:
                ...


def test_const_method() -> None:
    world.include(antidote_injectable)

    @injectable
    class Conf:
        def __init__(self, **kwargs: object) -> None:
            self.data = kwargs or {"test": object()}

        @const.factory.method
        def get(self, key: str) -> Box[object]:
            return Box(self.data[key])

        @const.factory.method
        def get2(self, key: str) -> Box[object]:
            return Box(self.data[key])

        A: Dependency[Box[object]] = get("test")
        DIFFERENT_ORIGIN = get2("test")

        with pytest.raises(TypeError):
            get("y", 2)  # type: ignore

    with pytest.raises(TypeError):
        Conf.get(key="y", b=2)  # type: ignore

    B: Dependency[Box[object]] = Conf.get("test")

    a = world[Conf.A]
    assert a == Box(world[Conf].data["test"])
    # singleton
    assert a is world[Conf.A]

    # Using the same Conf instance
    assert world[B] == a
    assert world[B] is world[B]
    assert world[Conf.DIFFERENT_ORIGIN] == a

    assert Conf.get.__wrapped__(Conf(test=x), "test") == Box(x)

    assert "DIFFERENT_ORIGIN" in repr(Conf.DIFFERENT_ORIGIN)
    assert "DIFFERENT_ORIGIN" in world.debug(Conf.DIFFERENT_ORIGIN)

    with world.test.clone() as overrides:
        overrides[Conf] = Conf(test="hello")
        a = world[Conf.A]
        # use existing Conf
        assert a == Box("hello")

        # while same const.factory.method, different value
        b = world[B]
        assert b == a
        assert b is not a
        assert b is world[B]


def test_private_const_method() -> None:
    world.include(antidote_injectable)

    @injectable(catalog=world.private)
    class Conf:
        def __init__(self, **kwargs: object) -> None:
            self.data = kwargs or {"test": object()}

        @const.factory.method
        def get(self, key: str) -> Box[object]:
            return Box(self.data[key])

        @const.factory.method
        def get2(self, key: str) -> Box[object]:
            return Box(self.data[key])

        A: Dependency[Box[object]] = get("test")
        DIFFERENT_ORIGIN = get2("test")

    B: Dependency[Box[object]] = Conf.get("test")

    a = world[Conf.A]
    assert a == Box(world.private[Conf].data["test"])
    # singleton
    assert a is world[Conf.A]

    # Using the same Conf instance
    assert world[B] == a
    assert world[Conf.DIFFERENT_ORIGIN] == a

    with world.test.clone() as overrides:
        overrides.of(world.private)[Conf] = Conf(test="hello")
        a = world[Conf.A]
        # use existing Conf
        assert a == Box("hello")


def test_const_static_method() -> None:
    class Conf:
        with pytest.raises(TypeError, match="staticmethod"):

            @const.factory.method
            @staticmethod
            def failure(key: str) -> Box[str]:
                ...

        @staticmethod
        @const.factory
        def before(key: str) -> Box[str]:
            return Box(key)

        @const.factory
        @staticmethod
        def after(key: str) -> Box[str]:
            return Box(key)

        # staticmethod not callable in Python 3.8
        if callable(before):
            A: Dependency[Box[str]] = before("test")
            C: Dependency[Box[str]] = after("test")
        else:
            A: Dependency[Box[str]] = before.__func__("test")  # type: ignore
            C: Dependency[Box[str]] = after.__func__("test")  # type: ignore

        with pytest.raises(TypeError):
            after("y", 2)  # type: ignore

        with pytest.raises(TypeError):
            before("y", 2)  # type: ignore

    with pytest.raises(TypeError):
        Conf.after(key="y", b=2)  # type: ignore

    with pytest.raises(TypeError):
        Conf.before(key="y", b=2)  # type: ignore

    B: Dependency[Box[str]] = Conf.before("test")
    D: Dependency[Box[str]] = Conf.after("test")

    a = world[Conf.A]
    b = world[B]
    c = world[Conf.C]
    d = world[D]
    assert a == Box("test")
    # singleton
    assert a is world[Conf.A]
    assert len({a, b, c, d}) == 1
    assert len({id(a), id(b), id(c), id(d)}) == 4


def test_const_class_method() -> None:
    class Failure:
        with pytest.raises(TypeError, match="classmethod"):

            @const.factory
            @classmethod
            def failure(cls) -> Box[str]:
                ...

        with pytest.raises(TypeError, match="classmethod"):

            @const.factory.method
            @classmethod
            def failure2(cls) -> Box[str]:
                ...


def test_injection_and_type_hints() -> None:
    world.include(antidote_injectable)

    @injectable(catalog=world.private)
    class Dummy:
        pass

    with pytest.raises(NameError, match="Dummy"):

        @const.factory(type_hints_locals=None)
        def error(dummy: Dummy = inject.me()) -> object:
            return dummy

    @const.factory
    def fun(dummy: Dummy = inject.me()) -> Box[Dummy]:
        return Box(dummy)

    @const.factory
    @inject(dict(dummy=Dummy))
    def fun2(dummy: object = None) -> Box[object]:
        return Box(dummy)

    @const.factory(inject=None)
    def fun3(dummy: Dummy = inject.me()) -> Box[Dummy]:
        return Box(dummy)

    @injectable
    class Conf:
        @const.factory.method
        def method(self, dummy: Dummy = inject.me()) -> Box[Dummy]:
            return Box(dummy)

        @const.factory.method
        @inject(dict(dummy=Dummy))
        def method2(self, dummy: object = None) -> Box[object]:
            return Box(dummy)

        @const.factory.method(inject=None)
        def method3(self, dummy: Dummy = inject.me()) -> Box[Dummy]:
            return Box(dummy)

        @const.factory
        @staticmethod
        def static(dummy: Dummy = inject.me()) -> Box[Dummy]:
            return Box(dummy)

        @const.factory
        @staticmethod
        @inject(dict(dummy=Dummy))
        def static2(dummy: object = None) -> Box[object]:
            return Box(dummy)

        @const.factory(inject=None)
        @staticmethod
        def static3(dummy: Dummy = inject.me()) -> Box[Dummy]:
            return Box(dummy)

    A = fun()
    B = Conf.method()
    C = Conf.static()
    injected = Box(world.private[Dummy])
    not_injected = Box(inject.me())
    assert world[A] == injected
    assert world[B] == injected
    assert world[C] == injected

    A2 = fun2()
    B2 = Conf.method2()
    C2 = Conf.static2()
    assert world[A2] == injected
    assert world[B2] == injected
    assert world[C2] == injected

    A3 = fun3()
    B3 = Conf.method3()
    C3 = Conf.static3()
    assert world[A3] == not_injected
    assert world[B3] == not_injected
    assert world[C3] == not_injected


def test_catalog() -> None:
    catalog = new_catalog(include=[antidote_lazy, antidote_injectable])

    @const.factory(catalog=catalog)
    def fun(key: str) -> Box[str]:
        ...

    @injectable(catalog=catalog.private)
    class Conf:
        @const.factory.method(catalog=catalog)
        def method(self, key: str) -> Box[str]:
            ...

        @const.factory(catalog=catalog)
        @staticmethod
        def static(key: str) -> Box[str]:
            ...

    HOST = const.env(catalog=catalog)
    A = const("A", catalog=catalog)
    B = fun("B")
    C = Conf.method("C")
    D = Conf.static("D")

    assert HOST not in world
    assert A not in world
    assert B not in world
    assert C not in world
    assert D not in world

    assert HOST in catalog
    assert A in catalog
    assert B in catalog
    assert C in catalog
    assert D in catalog


def test_test_env() -> None:
    world.include(antidote_injectable)

    @const.factory
    def fun(key: str) -> Box[str]:
        return Box(key)

    @injectable
    class Conf:
        @const.factory.method
        def method(self, key: str) -> Box[str]:
            return Box(key)

        @const.factory
        @staticmethod
        def static(key: str) -> Box[str]:
            return Box(key)

    HOST: Dependency[Box[str]] = const.env(cast=Box)
    A = const(object())
    B = fun("B")
    C = Conf.method("C")
    D = Conf.static("D")

    host = world[HOST]
    a = world[A]
    b = world[B]
    c = world[C]
    d = world[D]

    with world.test.empty():
        assert HOST not in world
        assert A not in world
        assert B not in world
        assert C not in world
        assert D not in world

    with world.test.new():
        assert HOST not in world
        assert A not in world
        assert B not in world
        assert C not in world
        assert D not in world

    with world.test.clone():
        assert HOST in world
        assert A in world
        assert B in world
        assert C in world
        assert D in world
        assert world[HOST] == host
        assert world[HOST] is not host
        assert world[A] is a
        assert world[B] == b
        assert world[B] is not b
        assert world[C] == c
        assert world[C] is not c
        assert world[D] == d
        assert world[D] is not d

    with world.test.copy():
        assert HOST in world
        assert A in world
        assert B in world
        assert C in world
        assert D in world
        assert world[HOST] is host
        assert world[A] is a
        assert world[B] is b
        assert world[C] is c
        assert world[D] is d
