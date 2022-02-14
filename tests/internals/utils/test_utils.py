from contextlib import contextmanager

import pytest
from typing_extensions import Annotated, Protocol, runtime_checkable

from antidote._internal.utils import enforce_type_if_possible


@contextmanager
def does_not_raise():
    yield


does_raise = pytest.raises(TypeError, match="(?i).*Value.*")


class DummyProtocol(Protocol):
    def dummy(self) -> None:
        pass


@runtime_checkable
class DummyRuntimeProtocol(Protocol):
    def dummy(self) -> None:
        pass


class ValidDummy:
    def dummy(self) -> None:
        pass


class InvalidDummy:
    pass


class SubDummy(ValidDummy):
    pass


@pytest.mark.parametrize('expectation, obj, tpe', [
    (does_raise, object(), int),
    (does_not_raise(), object(), Annotated[ValidDummy, object()]),
    (does_not_raise(), 1, int),
    (does_not_raise(), 1, DummyProtocol),
    (does_raise, 1, DummyRuntimeProtocol),
    (does_not_raise(), InvalidDummy(), DummyProtocol),
    (does_raise, InvalidDummy(), DummyRuntimeProtocol),
    (does_not_raise(), ValidDummy(), DummyProtocol),
    (does_not_raise(), ValidDummy(), DummyRuntimeProtocol),
    (does_not_raise(), SubDummy(), DummyProtocol),
    (does_not_raise(), SubDummy(), DummyRuntimeProtocol),
    (does_not_raise(), SubDummy(), ValidDummy),
    (does_raise, InvalidDummy(), ValidDummy),
])
def test_enforce_type(expectation, obj, tpe):
    with expectation:
        enforce_type_if_possible(obj, tpe)
