from __future__ import annotations

from typing import Generic, Optional, TypeVar
from typing_extensions import Protocol

SelfAnyPredicateWeight = TypeVar('SelfAnyPredicateWeight', bound='AnyPredicateWeight')
SelfPredicate = TypeVar('SelfPredicate', bound='Predicate')
P = TypeVar('P', bound='Predicate')


class AntidotePredicateWeight:
    predicate: Predicate

    def __init__(self, predicate: Predicate) -> None:
        self.predicate = predicate

    def __lt__(self, other: AntidotePredicateWeight) -> bool:
        raise RuntimeError("Antidote own weight logic is not defined yet "
                           "as only QualifiedBy exists as of now.")

    def __add__(self, other: AntidotePredicateWeight) -> AntidotePredicateWeight:
        raise RuntimeError("Antidote own weight logic is not defined yet "
                           "as only QualifiedBy exists as of now.")


class AnyPredicateWeight(Protocol):
    def __lt__(self: SelfAnyPredicateWeight,
               other: SelfAnyPredicateWeight | AntidotePredicateWeight
               ) -> bool:
        ...

    def __add__(self: SelfAnyPredicateWeight,
                other: SelfAnyPredicateWeight | AntidotePredicateWeight
                ) -> SelfAnyPredicateWeight:
        ...


class Predicate:
    def __and__(self: SelfPredicate, other: SelfPredicate) -> SelfPredicate:
        raise RuntimeError(f"Predicate {type(self)} does not support __and__,"
                           f"so you cannot specify more than one at once!")

    def weight(self) -> Optional[AnyPredicateWeight]:
        raise NotImplementedError()


class PredicateConstraint(Generic[P]):
    def __call__(self, predicate: Optional[P]) -> bool:
        raise NotImplementedError()
