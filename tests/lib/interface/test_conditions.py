# pyright: reportUnusedClass=false
from __future__ import annotations

import itertools
from typing import Any, Iterable, Sequence, TypeVar

import pytest

from antidote import implements, instanceOf, interface, world
from antidote.lib.interface import antidote_interface, NeutralWeight
from antidote.lib.interface.predicate import HeterogeneousWeightError
from tests.lib.interface.common import (
    _,
    only_if,
    OnlyIf,
    OnlyIf2,
    weighted,
    Weighted,
    Weighted2,
    weighted_alt,
    WeightedAlt,
)

T = TypeVar("T")


@pytest.fixture(autouse=True)
def setup_world() -> None:
    world.include(antidote_interface)


def test_neutral_weight() -> None:
    neutral = NeutralWeight()
    assert NeutralWeight() is neutral
    neutral += NeutralWeight()
    assert NeutralWeight() is neutral
    assert not (NeutralWeight() < neutral)
    assert repr(NeutralWeight()) == NeutralWeight.__name__
    assert NeutralWeight.of_neutral_predicate(Weighted(1.0)) is neutral
    assert NeutralWeight.neutral() is neutral


def test_boolean_condition() -> None:
    @interface
    class Base:
        ...

    @_(implements(Base).when(only_if(True)))
    class Yes(Base):
        ...

    @_(implements(Base).when(only_if(False)))
    class No(Base):
        ...

    assert isinstance(world[Base], Yes)


def test_weight_condition() -> None:
    @interface
    class Base:
        ...

    @_(implements(Base).when(weighted(12)))
    class Yes(Base):
        ...

    @_(implements(Base).when(weighted(1), weighted(2), weighted(3), weighted(4), NeutralWeight()))
    class No(Base):
        ...

    @_(implements(Base).when(weighted(None)))
    class Never(Base):
        ...

    assert isinstance(world[Base], Yes)
    out = world[instanceOf[Base]().all()]
    assert len(out) == 2
    assert all(isinstance(e, (Yes, No)) for e in out)


def test_weighted_predicate_condition() -> None:
    @interface
    class Base:
        ...

    @_(implements(Base).when(Weighted(12)))
    class Yes(Base):
        ...

    @_(implements(Base).when(Weighted(7), Weighted2(3)))
    class No(Base):
        ...

    @_(implements(Base).when(Weighted(None)))
    class Never(Base):
        ...

    assert isinstance(world[Base], Yes)
    out = world[instanceOf[Base]().all()]
    assert len(out) == 2
    assert all(isinstance(e, (Yes, No)) for e in out)


def test_neutral_predicate_condition() -> None:
    @interface
    class Base:
        ...

    @_(implements(Base).when(OnlyIf(True)))
    class Yes(Base):
        ...

    @_(implements(Base).when(OnlyIf(False)))
    class No(Base):
        ...

    assert isinstance(world[Base], Yes)


def test_neutral_and_weighted_predicate_condition() -> None:
    @interface
    class Base:
        ...

    @_(implements(Base).when(OnlyIf(True), OnlyIf2(True), Weighted(1)))
    class Yes(Base):
        ...

    @_(implements(Base).when(OnlyIf(True), OnlyIf2(True)))
    class No(Base):
        ...

    assert isinstance(world[Base], Yes)


def test_invalid_condition() -> None:
    @interface
    class Base:
        ...

    with pytest.raises(TypeError, match="predicate"):

        @_(implements(Base).when(object()))  # type: ignore
        class A(Base):
            ...


def test_duplicate_predicates() -> None:
    @interface
    class Base:
        ...

    @_(implements(Base).when(Weighted(1), Weighted(2), Weighted(3)))
    class A(Base):
        ...

    @_(implements(Base).when(Weighted(5)))
    class B(Base):
        ...

    assert isinstance(world[Base], A)

    with pytest.raises(TypeError, match="multiple predicates.*MergeablePredicate"):

        @_(implements(Base).when(Weighted2(5), Weighted2(5)))
        class C(Base):
            ...


def iter_sub_combinations(*args: T) -> Iterable[Iterable[T]]:
    return itertools.chain(
        *(
            itertools.permutations(comb, n)
            for n in range(1, len(args) + 1)
            for comb in itertools.combinations(args, n)
        )
    )


def test_simple_multiple_conditions() -> None:
    @interface
    class Base:
        ...

    # Ensures typing works correctly
    @_(implements(Base).when(only_if(True), OnlyIf(True), weighted(1), Weighted(1)))
    class A(Base):
        ...

    @_(implements(Base))
    class B(Base):
        ...

    assert isinstance(world[Base], A)


@pytest.mark.parametrize(
    "conditions", iter_sub_combinations(only_if(True), OnlyIf(True), weighted(5), Weighted(5))
)
def test_multiple_conditions(conditions: Sequence[Any]) -> None:
    @interface
    class Base:
        ...

    # Ensures ordering does not matter
    @_(implements(Base).when(*conditions))
    class A(Base):
        ...

    @_(implements(Base).when(weighted(-99)))
    class B(Base):
        ...

    assert isinstance(world[Base], A)


@pytest.mark.parametrize(
    "conditions",
    itertools.chain(
        itertools.permutations([only_if(False), OnlyIf(True), weighted(5), Weighted(5)], 4),
        itertools.permutations([only_if(True), OnlyIf(False), weighted(5), Weighted(5)], 4),
        itertools.permutations([only_if(True), OnlyIf(True), weighted(None), Weighted(5)], 4),
        itertools.permutations([only_if(True), OnlyIf(True), weighted(5), Weighted(None)], 4),
    ),
)
def test_multiple_conditions_one_false(conditions: Sequence[Any]) -> None:
    @interface
    class Base:
        ...

    @_(implements(Base))
    class A(Base):
        ...

    @_(implements(Base).when(*conditions))
    class B(Base):
        ...

    assert isinstance(world[Base], A)
    out = world[instanceOf[Base]().all()]
    assert len(out) == 1
    assert isinstance(out[0], A)


@pytest.mark.parametrize(
    "conditions",
    itertools.chain.from_iterable(
        itertools.product(*couple)  # type: ignore
        for couple in itertools.permutations(
            [[weighted(1.0), Weighted(1.0)], [weighted_alt(1.0), WeightedAlt(1.0)]], 2
        )
    ),
)
def test_multiple_weights(conditions: Sequence[Any]) -> None:
    @interface
    class Base:
        ...

    with pytest.raises(HeterogeneousWeightError, match="(Weight.*WeightAlt|WeightAlt.*Weight)"):

        @_(implements(Base).when(*conditions))
        class Impl(Base):
            ...


def test_different_weight_implementation() -> None:
    @interface
    class Base:
        ...

    @_(implements(Base).when(weighted(1.0)))
    class Impl1(Base):
        ...

    with pytest.raises(HeterogeneousWeightError, match="(Weight.*WeightAlt|WeightAlt.*Weight)"):

        @_(implements(Base).when(weighted_alt(1.0)))
        class Impl2(Base):
            ...


def test_ordering() -> None:
    @interface
    class Base:
        ...

    @_(implements(Base).when(weighted(1.0), qualified_by="a"))
    class Impl(Base):
        ...

    assert isinstance(world[Base], Impl)

    @_(implements(Base).when(weighted(10.0)))
    class Impl2(Base):
        ...

    assert isinstance(world[Base], Impl2)

    @_(implements(Base).when(weighted(5.0), qualified_by="a"))
    class Impl3(Base):
        ...

    assert isinstance(world[instanceOf[Base]().single(qualified_by="a")], Impl3)

    @_(implements(Base).when(weighted(10.0), qualified_by="a"))
    class Impl4(Base):
        ...

    assert isinstance(world[instanceOf[Base]().single(qualified_by="a")], Impl4)
