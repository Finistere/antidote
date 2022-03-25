from __future__ import annotations

import inspect
from typing import Optional

from .predicate import Predicate, PredicateConstraint


class QualifiedBy(Predicate, PredicateConstraint['QualifiedBy']):
    qualifiers: list[object]

    @classmethod
    def one_of(cls, *qualifiers: object) -> PredicateConstraint[QualifiedBy]:
        return QualifiedByOneOf(*qualifiers)

    @classmethod
    def instance_of(cls, klass: type) -> PredicateConstraint[QualifiedBy]:
        return QualifiedByInstanceOf(klass)

    def __init__(self, *qualifiers: object):
        if len(qualifiers) == 0:
            raise ValueError("At least one qualifier must be given.")

        for qualifier in qualifiers:
            if qualifier is None or isinstance(qualifier, (int, str, list, dict, tuple)):
                raise TypeError("A qualifier cannot ")
        self.qualifiers = sorted(qualifiers, key=id)

    def __call__(self, predicate: Optional[QualifiedBy]) -> bool:
        if predicate is None:
            return False

        if len(self.qualifiers) != len(predicate.qualifiers):
            return False

        for a, b in zip(self.qualifiers, predicate.qualifiers):
            if a is not b:
                return False

        return True

    def weight(self) -> int:
        return 1


class QualifiedByOneOf(PredicateConstraint[QualifiedBy]):
    def __init__(self, *qualifiers: object):
        self._qualifiers = QualifiedBy(*qualifiers).qualifiers

    def __call__(self, predicate: Optional[QualifiedBy]) -> bool:
        if predicate is None:
            return False

        i = 0
        j = 0
        while i < len(self._qualifiers) and j < len(predicate.qualifiers):
            a = self._qualifiers[i]
            b = predicate.qualifiers[j]
            if a is b:
                return True
            if id(a) < id(b):
                i += 1
            else:
                j += 1

        return False


class QualifiedByInstanceOf(PredicateConstraint[QualifiedBy]):
    def __init__(self, klass: type):
        if not (isinstance(klass, type) and inspect.isclass(klass)):
            raise TypeError(f"qualifier_type must be a class, not a {type(klass)}")
        self._klass = klass

    def __call__(self, predicate: Optional[QualifiedBy]) -> bool:
        if predicate is None:
            return False

        return any(isinstance(qualifier, self._klass) for qualifier in predicate.qualifiers)
