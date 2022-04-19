# pyright: reportUnusedClass=false
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Optional, TypeVar

import pytest

from antidote import implements, interface, world
from antidote.lib.injectable import register_injectable_provider
from antidote.lib.interface import (NeutralWeight, Predicate, QualifiedBy,
                                    register_interface_provider)

T = TypeVar('T')


def _(x: T) -> T:
    return x


@pytest.fixture(autouse=True)
def setup_world() -> Iterator[None]:
    with world.test.empty():
        register_injectable_provider()
        register_interface_provider()
        yield


class Weight:
    def __init__(self, weight: float) -> None:
        self.value = weight

    @classmethod
    def of_neutral(cls, predicate: Optional[Predicate[Any]]) -> Weight:
        if isinstance(predicate, QualifiedBy):
            return Weight(len(predicate.qualifiers))
        return Weight(1 if predicate is not None else 0)

    def __lt__(self, other: Weight) -> bool:
        return self.value < other.value

    def __add__(self, other: Weight) -> Weight:
        return Weight(self.value + other.value)

    def __str__(self) -> str:
        return f"{self.value}"  # pragma: no cover


class OnPath:
    def weight(self) -> Weight:
        return Weight(1.0 / len(self.path))

    def __init__(self, path: str) -> None:
        self.path = path


class WithPrefix:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def evaluate(self, predicate: Optional[OnPath]) -> bool:
        if predicate is None:
            return False

        return predicate.path.startswith(self.prefix)


class Version:
    def __init__(self, major: int):
        self.major = major

    def evaluate(self, predicate: Optional[Version]) -> bool:
        assert predicate is not None
        return predicate.major == self.major

    def weight(self) -> Weight:
        return Weight(self.major)


V1 = Version(1)
V2 = Version(2)


def test_custom_predicate_weight() -> None:
    @interface
    class Route:
        pass

    # similar paths
    @_(implements(Route).when(OnPath("/public"), V1))
    class Public(Route):
        pass

    @_(implements(Route).when(OnPath("/public/test"), V1))
    class PublicTest(Route):
        pass

    @implements(Route)
    class Nothing(Route):
        pass

    @_(implements(Route).when(qualified_by=object()))
    class QualifiedNothing(Route):
        pass

    public = world.get(Public)
    public_test = world.get(PublicTest)
    assert world.get[Route].all(WithPrefix("/public")) == [public, public_test]
    assert world.get[Route].single(WithPrefix("/public")) is public

    # versions
    @_(implements(Route).when(OnPath("/assets"), V1))
    class Assets(Route):
        pass

    @_(implements(Route).when(OnPath("/assets"), V2))
    class AssetsV2(Route):
        pass

    assert world.get[Route].single(WithPrefix("/assets")) is world.get(AssetsV2)
    assert world.get[Route].single(WithPrefix("/assets"), V1) is world.get(Assets)

    # qualifiers
    @_(implements(Route).when(OnPath("/example/dummy"), V1,
                              qualified_by=[object(), object(), object()]))
    class Example(Route):
        pass

    @_(implements(Route).when(OnPath("/example"), V2))
    class ExampleV2(Route):
        pass

    assert world.get[Route].single(WithPrefix("/example")) is world.get(Example)


class UseMe:
    def __init__(self, condition: bool) -> None:
        self.condition = condition

    def weight(self) -> Optional[Weight]:
        return Weight(1) if self.condition else None


def test_custom_predicate_condition() -> None:
    @interface
    class Base:
        pass

    @_(implements(Base).when(UseMe(False)))
    class NotUsed(Base):
        pass

    @_(implements(Base).when(UseMe(True)))
    class Used(Base):
        pass

    assert world.get[Base].single() is world.get(Used)


@dataclass(frozen=True, unsafe_hash=True, eq=True)
class Weighted:
    value: float

    @classmethod
    def merge(cls, a: Weighted, b: Weighted) -> Weighted:
        return Weighted(a.value + b.value)

    def weight(self) -> Weight:
        return Weight(self.value)


@dataclass(frozen=True, unsafe_hash=True, eq=True)
class GreaterThan:
    value: float

    @classmethod
    def merge(cls, a: GreaterThan, b: GreaterThan) -> GreaterThan:
        return GreaterThan(a.value + b.value)

    def evaluate(self, predicate: Optional[Weighted]) -> bool:
        if predicate is None:
            return False

        return self.value < predicate.value


def test_predicate_merge_typeclasses() -> None:
    @interface
    class Base:
        pass

    @_(implements(Base).when(Weighted(4)))
    class A(Base):
        pass

    @_(implements(Base).when(Weighted(3), Weighted(3)))
    class B(Base):
        pass

    @implements(Base)
    class C(Base):
        pass

    assert world.get[Base].all(GreaterThan(5)) == [world.get(B)]
    assert world.get[Base].all(GreaterThan(3), GreaterThan(3), GreaterThan(-1)) == [world.get(B)]
    assert world.get[Base].all(GreaterThan(123)) == []
    assert world.get[Base].all() == [world.get(B), world.get(A), world.get(C)]


def test_custom_predicate_constraint_missing_predicate() -> None:
    class NotQualified:
        def evaluate(self, predicate: Optional[QualifiedBy]) -> bool:
            return predicate is None

    @interface
    class Base:
        pass

    @_(implements(Base))
    class A(Base):
        pass

    @_(implements(Base).when(qualified_by=[object()]))
    class B(Base):
        pass

    a = world.get(A)
    b = world.get(B)

    assert set(world.get[Base].all()) == {a, b}
    assert world.get[Base].single(NotQualified()) is a


def test_custom_predicate_neutral_weight() -> None:
    class Dummy:
        def weight(self) -> NeutralWeight:
            return NeutralWeight()

    @interface
    class Base:
        pass

    x = object()

    @_(implements(Base).when(Dummy(), qualified_by=x))
    class A(Base):
        pass

    @_(implements(Base).when(UseMe(True), Weighted(1)))
    class B(Base):
        pass

    assert world.get[Base].single(qualified_by=x) is world.get(A)


@dataclass
class LocaleIs:
    lang: str

    def weight(self) -> Weight:
        return Weight(1000 if self.lang != 'en' else 500)

    def evaluate(self, predicate: Optional[LocaleIs]) -> bool:
        assert predicate is not None
        return self.lang == predicate.lang or predicate.lang == 'en'


def test_lang_example() -> None:
    @interface
    class Alert:
        ...

    @_(implements(Alert).when(LocaleIs('fr')))
    class FrenchAlert(Alert):
        ...

    @_(implements(Alert).when(LocaleIs('en')))
    class DefaultAlert(Alert):
        ...

    assert world.get[Alert].single(LocaleIs("fr")) is world.get(FrenchAlert)
    assert world.get[Alert].single(LocaleIs("it")) is world.get(DefaultAlert)
    assert world.get[Alert].single(LocaleIs("en")) is world.get(DefaultAlert)
