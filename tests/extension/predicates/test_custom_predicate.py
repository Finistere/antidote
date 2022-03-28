from __future__ import annotations

from typing import Optional

import pytest

from antidote import implements, interface, world
from antidote._providers import ServiceProvider
from antidote.extension.predicates import (AntidotePredicateWeight, Predicate, PredicateConstraint,
                                           QualifiedBy, register_interface_provider)


def _(x):
    return x


@pytest.fixture(autouse=True)
def setup_world():
    with world.test.empty():
        world.provider(ServiceProvider)
        register_interface_provider()
        yield


class Weight:
    def __init__(self, weight: float) -> None:
        self.value = weight

    def __lt__(self, other: Weight | AntidotePredicateWeight) -> bool:
        if isinstance(other, AntidotePredicateWeight):
            assert isinstance(other.predicate, QualifiedBy)
            return self.value < len(other.predicate.qualifiers)
        else:
            return self.value < other.value

    def __add__(self,
                other: Weight | AntidotePredicateWeight
                ) -> Weight:
        if isinstance(other, AntidotePredicateWeight):
            assert isinstance(other.predicate, QualifiedBy)
            return Weight(self.value + len(other.predicate.qualifiers))
        else:
            return Weight(self.value + other.value)

    def __str__(self) -> str:
        return f"{self.value}"


class OnPath(Predicate):
    def weight(self) -> Weight:
        return Weight(1.0 / len(self.path))

    def __init__(self, path: str) -> None:
        self.path = path


class WithPrefix(PredicateConstraint[OnPath]):
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def __call__(self, predicate: Optional[OnPath]) -> bool:
        if predicate is None:
            return False

        return predicate.path.startswith(self.prefix)


class Version(Predicate, PredicateConstraint['Version']):
    def __init__(self, major: int):
        self.major = major

    def __call__(self, predicate: Optional[Version]) -> bool:
        return predicate.major == self.major

    def weight(self) -> Weight:
        return Weight(self.major)


V1 = Version(1)
V2 = Version(2)


def test_custom_predicate_weight():
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

    public = world.get(Public)
    public_test = world.get(PublicTest)
    assert set(world.get[Route].all(WithPrefix("/public"))) == {public_test, public}
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
