import gc
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, ContextManager, Iterator

import pytest
from typing_extensions import Protocol, runtime_checkable

from antidote._internal import enforce_subclass_if_possible, Singleton
from antidote._internal.utils import CachedMeta
from tests.utils import Box


@contextmanager
def does_not_raise() -> Iterator[None]:
    yield


does_raise = pytest.raises(TypeError, match="(?i).*(isinstance|subclass|implement).*")


class DummyProtocol(Protocol):
    def dummy(self) -> None:
        ...


@runtime_checkable
class DummyRuntimeProtocol(Protocol):
    def dummy(self) -> None:
        ...


class ValidDummy:
    def dummy(self) -> None:
        ...


class InvalidDummy:
    pass


class SubDummy(ValidDummy):
    pass


@pytest.mark.parametrize(
    "expectation, sub, tpe",
    [
        (does_not_raise(), ValidDummy, DummyProtocol),
        (does_not_raise(), ValidDummy, DummyRuntimeProtocol),
        (does_not_raise(), InvalidDummy, DummyProtocol),
        (does_raise, InvalidDummy, DummyRuntimeProtocol),
        (does_raise, InvalidDummy, ValidDummy),
        (does_not_raise(), SubDummy, ValidDummy),
        (does_not_raise(), 1, 1),
        (does_not_raise(), 1, int),
        (does_not_raise(), int, 1),
    ],
)
def test_enforce_subtype(expectation: ContextManager[Any], sub: type, tpe: type) -> None:
    with expectation:
        enforce_subclass_if_possible(sub, tpe)


def test_singleton() -> None:
    class Dummy(Singleton):
        pass

    assert Dummy() is Dummy()


def test_cached_instances() -> None:
    @dataclass(eq=True, unsafe_hash=True)
    class Dummy(metaclass=CachedMeta):
        __slots__ = ("value", "__weakref__")
        value: Box[str]

        def __init__(self, value: Box[str]) -> None:
            self.value = value

        def __repr__(self) -> str:
            return "Dummy"

    hello = Box("hello")
    a = Dummy(hello)
    assert a.value is hello
    assert Dummy(hello) is a
    assert Dummy(Box("hello")) is a
    assert Dummy(Box("Different")) is not a

    john = Box("John")

    def f() -> None:
        Dummy(john)  # create instance without keeping a reference to it

    f()
    gc.collect()

    b = Dummy(Box("John"))
    assert b.value is not john
