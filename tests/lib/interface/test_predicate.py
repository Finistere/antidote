# pyright: reportUnusedClass=false
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Optional, TypeVar

import pytest

from antidote import implements, inject, injectable, interface, world
from antidote.lib.injectable import register_injectable_provider
from antidote.lib.interface import NeutralWeight, predicate, Predicate, register_interface_provider

T = TypeVar('T')


def _(x: T) -> T:
    return x


@dataclass
class Weight:
    value: int

    @classmethod
    def of_neutral(cls, predicate: Optional[Predicate[Any]]) -> Weight:
        return Weight(0)

    def __lt__(self, other: Weight) -> bool:
        return self.value < other.value

    def __add__(self, other: Weight) -> Weight:
        return Weight(self.value + other.value)


@pytest.fixture(autouse=True)
def setup_world() -> Iterator[None]:
    with world.test.empty():
        register_injectable_provider()
        register_interface_provider()
        yield


def test_neutral_weight() -> None:
    neutral = NeutralWeight()
    assert NeutralWeight() is neutral
    assert (NeutralWeight() + NeutralWeight()) == neutral
    assert not (NeutralWeight() < neutral)


@predicate
def only_if(condition: bool) -> bool:
    return condition


@predicate
def weighted(value: Optional[int] = None) -> Optional[Weight]:
    return Weight(value) if value is not None else None


def test_simple_predicate() -> None:
    assert isinstance(only_if(True), Predicate)
    assert only_if(False).weight() is None
    assert only_if(True).weight() is NeutralWeight()

    assert isinstance(weighted(0), Predicate)
    assert weighted().weight() is None
    assert weighted(12).weight() == Weight(12)


def test_predicate_implements() -> None:
    @interface
    class Base:
        ...

    @_(implements(Base).when(only_if(True)))
    class Yes(Base):
        ...

    @_(implements(Base).when(only_if(False)))
    class No(Base):
        ...

    assert world.get(Base) is world.get(Yes)


def test_multiple_predicates() -> None:
    @interface
    class Base:
        ...

    @_(implements(Base).when(only_if(True), weighted(12)))
    class Yes(Base):
        ...

    assert world.get(Base) is world.get(Yes)

    with pytest.raises(RuntimeError):
        @_(implements(Base).when(only_if(True), only_if(True)))
        class Invalid(Base):
            ...

    with pytest.raises(RuntimeError):
        @_(implements(Base).when(weighted(12), weighted(12)))
        class Invalid2(Base):
            ...


def test_predicate_generated_class() -> None:
    p = only_if(True)
    assert type(p).__name__ == "OnlyIfPredicate"
    assert str(p) == "OnlyIfPredicate(_weight=NeutralWeight)"

    p2 = weighted(12)
    assert type(p2).__name__ == "WeightedPredicate"
    assert str(p2) == "WeightedPredicate(_weight=Weight(value=12))"


def test_predicate_invalid_function() -> None:
    with pytest.raises(TypeError):
        predicate(object())  # type: ignore


def test_predicate_already_injected() -> None:
    @injectable
    class Dummy:
        ...

    @predicate
    @inject({'dummy': Dummy})
    def if_only(condition: bool, dummy: Dummy) -> bool:
        return condition

    @interface
    class Base:
        ...

    @_(implements(Base).when(if_only(True)))
    class Yes(Base):
        ...

    assert world.get(Base) is world.get(Yes)
