from __future__ import annotations

import inspect
import itertools
from typing import Optional

from .predicate import AntidotePredicateWeight, AnyPredicateWeight, Predicate, PredicateConstraint
from ..._internal.utils import FinalImmutable

_BUILTIN_TYPES = (int, float, str, list, dict, set, tuple, bytes, bytearray, bool, complex)


class QualifiedBy(FinalImmutable, Predicate, PredicateConstraint['QualifiedBy']):
    __slots__ = ('qualifiers',)
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
            if qualifier is None or isinstance(qualifier, _BUILTIN_TYPES):
                raise TypeError(f"Invalid qualifier: {qualifier!r}. "
                                f"It cannot be None or an instance of a builtin type")
        super().__init__(qualifiers=[
            next(group)
            for k, group in itertools.groupby(sorted(qualifiers, key=id), key=id)
        ])

    def __call__(self, predicate: Optional[QualifiedBy]) -> bool:
        if predicate is None:
            return False

        if len(self.qualifiers) != len(predicate.qualifiers):
            return False

        for a, b in zip(self.qualifiers, predicate.qualifiers):
            if a is not b:
                return False

        return True

    def __and__(self, other: QualifiedBy) -> QualifiedBy:
        return QualifiedBy(*self.qualifiers, *other.qualifiers)

    def weight(self) -> AnyPredicateWeight:
        return AntidotePredicateWeight(self)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, QualifiedBy) and self(other)

    def __hash__(self) -> int:
        return hash(tuple(id(q) for q in self.qualifiers))


class QualifiedByOneOf(FinalImmutable, PredicateConstraint[QualifiedBy]):
    __slots__ = ('__qualified_by',)
    __qualified_by: QualifiedBy

    def __init__(self, *qualifiers: object):
        super().__init__(QualifiedBy(*qualifiers))

    def __call__(self, predicate: Optional[QualifiedBy]) -> bool:
        if predicate is None:
            return False

        li = 0
        ri = 0
        while li < len(self.__qualified_by.qualifiers) and ri < len(predicate.qualifiers):
            left = self.__qualified_by.qualifiers[li]
            right = predicate.qualifiers[ri]
            if left is right:
                return True
            if id(left) < id(right):
                li += 1
            else:
                ri += 1

        return False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, QualifiedByOneOf) and self.__qualified_by == other.__qualified_by

    def __hash__(self) -> int:
        return hash(self.__qualified_by)


class QualifiedByInstanceOf(FinalImmutable, PredicateConstraint[QualifiedBy]):
    __slots__ = ('__klass',)
    __klass: type

    def __init__(self, klass: type):
        if not (isinstance(klass, type) and inspect.isclass(klass)):
            raise TypeError(f"qualifier_type must be a class, not a {type(klass)}")
        super().__init__(klass)

    def __call__(self, predicate: Optional[QualifiedBy]) -> bool:
        if predicate is None:
            return False

        return any(isinstance(qualifier, self.__klass) for qualifier in predicate.qualifiers)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, QualifiedByInstanceOf) and self.__klass == other.__klass

    def __hash__(self) -> int:
        return hash(self.__klass)
