# pyright: reportUnusedClass=false
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, cast, Optional, Sequence, Type, TypeVar, Union

import pytest
from typing_extensions import Protocol

from antidote import implements, inject, injectable, instanceOf, interface, Predicate, world
from antidote.lib.injectable import antidote_injectable
from antidote.lib.interface import antidote_interface, NeutralWeight, QualifiedBy
from tests.lib.interface.common import _, Weight


@pytest.fixture(autouse=True)
def setup_world() -> None:
    world.include(antidote_interface)


class OnPath:
    def weight(self) -> Weight:
        return Weight(1.0 / len(self.path))

    def __init__(self, path: str) -> None:
        self.path = path


class WithPrefix:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def __call__(self, predicate: Optional[OnPath]) -> bool:
        if predicate is None:
            return False

        return predicate.path.startswith(self.prefix)


class Version:
    def __init__(self, major: int):
        self.major = major

    def __call__(self, predicate: Optional[Version]) -> bool:
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

    assert isinstance(world[instanceOf(Route).single(WithPrefix("/public"))], Public)
    a, b = world[instanceOf(Route).all(WithPrefix("/public"))]
    assert (isinstance(a, Public) and isinstance(b, PublicTest)) or (
        isinstance(b, Public) and isinstance(a, PublicTest)
    )

    # versions
    @_(implements(Route).when(OnPath("/assets"), V1))
    class Assets(Route):
        pass

    @_(implements(Route).when(OnPath("/assets"), V2))
    class AssetsV2(Route):
        pass

    assert isinstance(world[instanceOf(Route).single(WithPrefix("/assets"))], AssetsV2)
    assert isinstance(world[instanceOf(Route).single(WithPrefix("/assets"), V1)], Assets)

    # qualifiers
    @_(
        implements(Route).when(
            OnPath("/example/dummy"), V1, qualified_by=[object(), object(), object()]
        )
    )
    class Example(Route):
        pass

    @_(implements(Route).when(OnPath("/example"), V2))
    class ExampleV2(Route):
        pass

    assert isinstance(world[instanceOf(Route).single(WithPrefix("/example"))], Example)


class UseMe:
    def __init__(self, condition: bool) -> None:
        self.condition = condition

    def weight(self) -> Optional[Weight]:
        return Weight(1) if self.condition else None


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

    def __call__(self, predicate: Optional[Weighted]) -> bool:
        assert predicate is not None
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

    (b,) = world[instanceOf(Base).all(GreaterThan(5))]
    assert isinstance(b, B)
    assert world[instanceOf(Base).all(GreaterThan(3), GreaterThan(3), GreaterThan(-1))] == [b]
    assert world[instanceOf(Base).all(GreaterThan(123))] == []

    e1, e2 = world[instanceOf(Base).all()]
    assert e1 is b or e2 is b
    assert isinstance(e1, A) or isinstance(e2, A)


def test_custom_predicate_constraint_missing_predicate() -> None:
    def not_qualified(predicate: Optional[QualifiedBy]) -> bool:
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

    a = world[instanceOf(Base).single(not_qualified)]
    assert isinstance(a, A)
    e1, e2 = world[instanceOf(Base).all()]
    assert e1 is a or e2 is a
    assert isinstance(e1, B) or isinstance(e2, B)


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

    assert isinstance(world[instanceOf(Base).single(qualified_by=x)], A)


@dataclass
class LocaleIs:
    lang: str

    def weight(self) -> Weight:
        return Weight(1000 if self.lang != "en" else 500)

    def __call__(self, predicate: Optional[LocaleIs]) -> bool:
        assert predicate is not None
        return self.lang == predicate.lang or predicate.lang == "en"


def test_lang_example() -> None:
    @interface
    class Alert:
        ...

    @_(implements(Alert).when(LocaleIs("fr")))
    class FrenchAlert(Alert):
        ...

    @_(implements(Alert).when(LocaleIs("en")))
    class DefaultAlert(Alert):
        ...

    assert isinstance(world[instanceOf(Alert).single(LocaleIs("fr"))], FrenchAlert)
    assert isinstance(world[instanceOf(Alert).single(LocaleIs("it"))], DefaultAlert)
    assert isinstance(world[instanceOf(Alert).single(LocaleIs("en"))], DefaultAlert)


def test_event_subscriber_example() -> None:
    world.include(antidote_injectable)

    class Event:
        ...

    class InitializationEvent(Event):
        ...

    E = TypeVar("E", bound=Event, contravariant=True)

    @interface  # can be applied on protocols and "standard" classes
    class EventSubscriber(Protocol[E]):
        def process(self, event: E) -> None:
            ...

    # Ensures OnInitialization is really a EventSubscriber if possible
    @_(
        implements.protocol[EventSubscriber[InitializationEvent]]().when(
            qualified_by=InitializationEvent
        )
    )
    @injectable
    class OnInitialization:
        def __init__(self) -> None:
            self.called_with: list[InitializationEvent] = []

        def process(self, event: InitializationEvent) -> None:
            self.called_with.append(event)

    @inject
    def process_initialization(
        event: InitializationEvent,
        # injects all subscribers qualified by InitializationEvent
        subscribers: Sequence[EventSubscriber[InitializationEvent]] = inject.me(
            qualified_by=InitializationEvent
        ),
    ) -> None:
        for subscriber in subscribers:
            subscriber.process(event)

    sub: OnInitialization = world[OnInitialization]
    event = InitializationEvent()
    process_initialization(event)
    assert sub.called_with == [event]

    tpe = cast(Type[EventSubscriber[InitializationEvent]], EventSubscriber[InitializationEvent])
    process_initialization(
        event,
        # Explicitly retrieving the subscribers
        subscribers=world[instanceOf(tpe).all(qualified_by=InitializationEvent)],
    )
    assert sub.called_with == [event, event]

    process_initialization(
        event,
        # Explicitly retrieving the subscribers
        subscribers=world[instanceOf(tpe).all(qualified_by=object())],
    )
    assert sub.called_with == [event, event]


def test_invalid_constraints() -> None:
    @interface
    class Base:
        ...

    # PredicateConstraint #
    #######################
    with pytest.raises(TypeError, match="PredicateConstraint"):
        world[instanceOf(Base).single(object())]  # type: ignore

    with pytest.raises(TypeError, match="PredicateConstraint"):
        world[instanceOf(Base).all(object())]  # type: ignore

    with pytest.raises(TypeError, match="PredicateConstraint"):
        world[instanceOf[Base]().single(object())]  # type: ignore

    with pytest.raises(TypeError, match="PredicateConstraint"):
        world[instanceOf[Base]().all(object())]  # type: ignore

    with pytest.raises(TypeError, match="PredicateConstraint"):

        @inject
        def f(x: Base = inject.me(object())) -> None:  # type: ignore
            ...

    # qualified_by_one_of #
    #######################
    with pytest.raises(TypeError, match="qualified_by_one_of"):
        world[instanceOf(Base).single(qualified_by_one_of=object())]  # type: ignore

    with pytest.raises(TypeError, match="qualified_by_one_of"):
        world[instanceOf(Base).all(qualified_by_one_of=object())]  # type: ignore

    with pytest.raises(TypeError, match="qualified_by_one_of"):
        world[instanceOf[Base]().single(qualified_by_one_of=object())]  # type: ignore

    with pytest.raises(TypeError, match="qualified_by_one_of"):
        world[instanceOf[Base]().all(qualified_by_one_of=object())]  # type: ignore

    with pytest.raises(TypeError, match="qualified_by_one_of"):

        @inject
        def f2(x: Base = inject.me(qualified_by_one_of=object())) -> None:  # type: ignore
            ...

    class MissingArgumentPredicateConstraint:
        def __call__(self) -> bool:
            ...

    # MissingArgumentPredicateConstraint #
    ######################################
    with pytest.raises(TypeError, match="Missing an argument"):
        world[instanceOf(Base).single(MissingArgumentPredicateConstraint())]  # type: ignore

    with pytest.raises(TypeError, match="Missing an argument"):
        world[instanceOf(Base).all(MissingArgumentPredicateConstraint())]  # type: ignore

    with pytest.raises(TypeError, match="Missing an argument"):
        world[instanceOf[Base]().single(MissingArgumentPredicateConstraint())]  # type: ignore

    with pytest.raises(TypeError, match="Missing an argument"):
        world[instanceOf[Base]().all(MissingArgumentPredicateConstraint())]  # type: ignore

    with pytest.raises(TypeError, match="Missing an argument"):

        @inject
        def f3(x: Base = inject.me(MissingArgumentPredicateConstraint())) -> None:  # type: ignore
            ...

    class InvalidTypeHintPredicateConstraint:
        def __call__(self, predicate: int) -> bool:
            ...

    # InvalidTypeHintPredicateConstraint #
    ######################################
    with pytest.raises(TypeError, match="optional Predicate type hint"):
        world[instanceOf(Base).single(InvalidTypeHintPredicateConstraint())]  # type: ignore

    with pytest.raises(TypeError, match="optional Predicate type hint"):
        world[instanceOf(Base).all(InvalidTypeHintPredicateConstraint())]  # type: ignore

    with pytest.raises(TypeError, match="optional Predicate type hint"):
        world[instanceOf[Base]().single(InvalidTypeHintPredicateConstraint())]  # type: ignore

    with pytest.raises(TypeError, match="optional Predicate type hint"):
        world[instanceOf[Base]().all(InvalidTypeHintPredicateConstraint())]  # type: ignore

    with pytest.raises(TypeError, match="optional Predicate type hint"):

        @inject
        def f4(x: Base = inject.me(InvalidTypeHintPredicateConstraint())) -> None:  # type: ignore
            ...


def test_invalid_complex_predicate_type_hints() -> None:
    @interface
    class Base:
        ...

    def f1(predicate: Any) -> None:
        ...

    def f2(predicate: Union[int, float]) -> None:
        ...

    def f3(predicate: Optional[int]) -> None:
        ...

    def f4(predicate: Union[None, Predicate[Any], int]) -> None:
        ...

    def f5(predicate: Predicate[Any]) -> None:
        ...

    def f6(predicate) -> None:  # type: ignore
        ...

    with pytest.raises(TypeError, match="optional Predicate type hint"):
        world[instanceOf(Base).single(f1)]  # type: ignore

    with pytest.raises(TypeError, match="optional Predicate type hint"):
        world[instanceOf(Base).single(f2)]  # type: ignore

    with pytest.raises(TypeError, match="optional Predicate type hint"):
        world[instanceOf(Base).single(f3)]  # type: ignore

    with pytest.raises(TypeError, match="optional Predicate type hint"):
        world[instanceOf(Base).single(f4)]  # type: ignore

    with pytest.raises(TypeError, match="optional Predicate type hint"):
        world[instanceOf(Base).single(f5)]  # type: ignore

    with pytest.raises(TypeError, match="optional Predicate type hint"):
        world[instanceOf(Base).single(f6)]  # type: ignore


if sys.version_info >= (3, 10):

    def test_python310_support() -> None:
        @interface
        class Base:
            pass

        @implements(Base)
        class A(Base):
            pass

        @_(implements(Base).when(qualified_by=Base))
        class B(Base):
            pass

        @dataclass
        class NewUnionSyntaxTypeHint:
            expected: object

            def __call__(self, predicate: "QualifiedBy | None") -> bool:
                return predicate is not None and self.expected in predicate.qualifiers

        assert world[instanceOf(Base).all(NewUnionSyntaxTypeHint(object()))] == []
        assert isinstance(world[instanceOf(Base).single(NewUnionSyntaxTypeHint(Base))], B)
