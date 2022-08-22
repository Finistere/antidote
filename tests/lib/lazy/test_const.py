# pyright: reportUnusedFunction=false, reportUnusedClass=false
from __future__ import annotations

from enum import Enum
from typing import Any, Iterator, Tuple, TypeVar

import pytest

from antidote import (
    antidote_lib_injectable,
    antidote_lib_lazy,
    const,
    Dependency,
    inject,
    new_catalog,
    world,
)
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
        world.include(antidote_lib_lazy)
        yield


def test_debug() -> None:
    world.include(antidote_lib_injectable)

    HOST: Dependency[Box[str]] = const.env(convert=Box)
    A = const("Hello world!")

    line_number = 50
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


def test_simple_const() -> None:
    catalog = new_catalog(include=[antidote_lib_lazy])

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
    PORT: Dependency[int] = const.env(convert=int)
    CHOICE: Dependency[Choice] = const.env(convert=Choice)
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
        PORT: Dependency[int] = const.env(convert=int)
        CHOICE: Dependency[Choice] = const.env(convert=Choice)
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

    const.env(default=90, convert=int)  # should not fail
    with pytest.raises(TypeError, match="default.*convert"):
        const.env(default=90, convert=str)  # type: ignore

    with pytest.raises(TypeError, match="first argument"):
        const.env(object())  # type: ignore

    with pytest.raises(TypeError, match="convert"):
        HOST = const.env(convert=0)  # type: ignore


def test_catalog() -> None:
    catalog = new_catalog(include=[antidote_lib_lazy, antidote_lib_injectable])

    HOST = const.env(catalog=catalog)
    A = const("A", catalog=catalog)

    assert HOST not in world
    assert A not in world

    assert HOST in catalog
    assert A in catalog


def test_test_env() -> None:
    world.include(antidote_lib_injectable)

    HOST: Dependency[Box[str]] = const.env(convert=Box)
    A = const(object())

    host = world[HOST]
    a = world[A]

    with world.test.empty():
        assert HOST not in world
        assert A not in world

    with world.test.new():
        assert HOST not in world
        assert A not in world

    with world.test.clone():
        assert HOST in world
        assert A in world
        assert world[HOST] == host
        assert world[HOST] is not host
        assert world[A] is a

    with world.test.copy():
        assert HOST in world
        assert A in world
        assert world[HOST] is host
        assert world[A] is a
