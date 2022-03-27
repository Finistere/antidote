from __future__ import annotations

from typing import Generic, Optional, TypeVar

from typing_extensions import Protocol

SelfAnyPredicateWeight = TypeVar('SelfAnyPredicateWeight', bound='AnyPredicateWeight')
SelfPredicate = TypeVar('SelfPredicate', bound='Predicate')
SelfPredicateConstraint = TypeVar('SelfPredicateConstraint', bound='PredicateConstraint')
P = TypeVar('P', bound='Predicate')


class AntidotePredicateWeight:
    predicate: Predicate

    def __init__(self, predicate: Predicate) -> None:
        self.predicate = predicate

    def __lt__(self, other: AntidotePredicateWeight) -> bool:
        return False  # All predicates are currently strictly equal.

    def __add__(self, other: AntidotePredicateWeight) -> AntidotePredicateWeight:
        raise RuntimeError("Antidote own weight logic is not defined yet "
                           "as only QualifiedBy exists as of now.")  # pragma: no cover


class AnyPredicateWeight(Protocol):
    def __lt__(self: SelfAnyPredicateWeight,
               other: SelfAnyPredicateWeight | AntidotePredicateWeight
               ) -> bool:
        ...  # pragma: no cover

    def __add__(self: SelfAnyPredicateWeight,
                other: SelfAnyPredicateWeight | AntidotePredicateWeight
                ) -> SelfAnyPredicateWeight:
        ...  # pragma: no cover


class Predicate:
    def __and__(self: SelfPredicate, other: SelfPredicate) -> SelfPredicate:
        raise RuntimeError(f"Predicate {type(self)!r} does not support __and__,"
                           f"so you cannot specify more than one at once!")  # pragma: no cover

    def weight(self) -> Optional[AnyPredicateWeight]:
        raise NotImplementedError()  # pragma: no cover


class PredicateConstraint(Generic[P]):
    def __and__(self: SelfPredicateConstraint,
                other: SelfPredicateConstraint
                ) -> SelfPredicateConstraint:
        raise RuntimeError(f"PredicateConstraint {type(self)!r} "
                           f"does not support __and__.")  # pragma: no cover

    def __call__(self, predicate: Optional[P]) -> bool:
        raise NotImplementedError()  # pragma: no cover
