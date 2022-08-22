# pyright: reportUnusedClass=false
from __future__ import annotations

import itertools

import pytest

from antidote import antidote_lib_interface, implements, instanceOf, interface, QualifiedBy, world
from tests.lib.interface.common import _

x = object()
y = object()
z = object()


@pytest.fixture(autouse=True)
def setup_world() -> None:
    world.include(antidote_lib_interface)


def test_qualified_by_must_have_at_least_one_qualifier() -> None:
    with pytest.raises(ValueError, match="(?i).*at least one qualifier.*"):
        QualifiedBy()


def test_qualified_by_eq_hash() -> None:
    assert QualifiedBy(x) != object()
    assert QualifiedBy(x) == QualifiedBy(x)
    assert hash(QualifiedBy(x)) == hash(QualifiedBy(x))
    assert QualifiedBy(x) != QualifiedBy(y)
    assert hash(QualifiedBy(x)) != hash(QualifiedBy(y))

    assert QualifiedBy(x, y) == QualifiedBy(y, x)
    assert QualifiedBy(x, y) == QualifiedBy(y, y, x, x, y, x, y, x)


def test_qualified_by_predicate() -> None:
    assert QualifiedBy(object()).weight() is not None
    assert QualifiedBy.merge(QualifiedBy(x), QualifiedBy(y)) == QualifiedBy(x, y)


def test_qualified_by_predicate_constraint() -> None:
    assert QualifiedBy(x)(QualifiedBy(x))
    assert QualifiedBy(x, y)(QualifiedBy(x, y))
    assert QualifiedBy(x, y)(QualifiedBy(y, x))
    assert QualifiedBy(x)(QualifiedBy(x, y))
    assert QualifiedBy(y)(QualifiedBy(x, y))

    assert not QualifiedBy(x)(QualifiedBy(y))
    assert not QualifiedBy(x, y)(QualifiedBy(x))

    # on missing QualifiedBy
    assert not QualifiedBy(x)(None)


def test_qualified_by_one_of() -> None:
    assert QualifiedBy.one_of(x)(QualifiedBy(x))
    assert QualifiedBy.one_of(x)(QualifiedBy(x, y))

    assert QualifiedBy.one_of(x, y)(QualifiedBy(x))
    assert QualifiedBy.one_of(x, y)(QualifiedBy(x, y))
    assert QualifiedBy.one_of(x, y)(QualifiedBy(y))

    # Ensuring (roughly) we have all cases of ordering with id()
    for left in itertools.permutations([x, y, z]):
        for right in [x, y, z]:
            QualifiedBy.one_of(*left)(QualifiedBy(object(), right, object()))

    assert not QualifiedBy.one_of(x)(QualifiedBy(y))

    # on missing QualifiedBy
    assert not QualifiedBy.one_of(x)(None)


def test_only_qualifier_equality_matters() -> None:
    assert QualifiedBy("a")(QualifiedBy("a"))
    assert not QualifiedBy("a")(QualifiedBy("b"))
    assert QualifiedBy.one_of("a")(QualifiedBy("a", "b"))
    assert not QualifiedBy.one_of("a")(QualifiedBy("c", "b"))


def test_nothing() -> None:
    @interface
    class Base:
        ...

    @_(implements(Base).when(qualified_by="a"))
    class A(Base):
        ...

    @_(implements(Base))
    class B(Base):
        ...

    assert isinstance(world[instanceOf[Base]().single(QualifiedBy.nothing)], B)
