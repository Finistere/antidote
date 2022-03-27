from typing import Any, Optional, Union

import pytest

from antidote.extension.predicates import Predicate, PredicateConstraint, QualifiedBy
from antidote.extension.predicates._internal import create_constraints as create

x = object()
y = object()


def test_create_constraints_qualifiers():
    assert create(QualifiedBy(x)) == create(qualified_by=[x])
    assert create(QualifiedBy(x, y)) == create(qualified_by=[x, y])
    assert create(QualifiedBy.one_of(x)) == create(qualified_by_one_of=[x])
    assert create(QualifiedBy.one_of(x, y)) == create(qualified_by_one_of=[x, y])
    assert create(QualifiedBy.instance_of(int)) == create(qualified_by_instance_of=int)

    assert create(QualifiedBy(x)) == [(QualifiedBy, QualifiedBy(x))]
    assert create(QualifiedBy.one_of(x)) == [(QualifiedBy, QualifiedBy.one_of(x))]
    assert create(QualifiedBy.instance_of(int)) == [(QualifiedBy, QualifiedBy.instance_of(int))]


def test_create_invalid_kwargs():
    with pytest.raises(TypeError, match="(?i).*qualified_by.*"):
        create(qualified_by=object())

    with pytest.raises(TypeError, match="(?i).*qualified_by_one_of.*"):
        create(qualified_by_one_of=object())

    with pytest.raises(TypeError, match="(?i).*type.*"):
        create(qualified_by_instance_of=object())


def test_create_constraint_combination():
    assert create(QualifiedBy(x), QualifiedBy(x)) == create(QualifiedBy(x))
    assert create(QualifiedBy(x), QualifiedBy(y)) == create(QualifiedBy(x, y))
    assert create(QualifiedBy.one_of(x), QualifiedBy.one_of(x)) == create(QualifiedBy.one_of(x))
    assert set(create(QualifiedBy.one_of(x), QualifiedBy.one_of(y))) == {
        (QualifiedBy, QualifiedBy.one_of(x)),
        (QualifiedBy, QualifiedBy.one_of(y))
    }


def test_create_constraint_invalid_predicate_class():
    with pytest.raises(TypeError, match="(?i).*PredicateConstraint.*"):
        create(object())

    class MissingPredicateArgument(PredicateConstraint[Any]):
        def __call__(self, *args, **kwargs):
            pass

    with pytest.raises(TypeError, match="(?i).*'predicate' argument.*"):
        create(MissingPredicateArgument())


@pytest.mark.parametrize('type_hint', [
    Any,
    Union[int, float],
    Optional[int],
    Union[None, Predicate, int],
    Predicate
])
def test_create_constraint_invalid_type_hint(type_hint):
    class InvalidTypeHint(PredicateConstraint[Any]):
        def __call__(self, predicate: type_hint):
            pass

    with pytest.raises(TypeError, match="(?i).*Optional.*Predicate.*"):
        create(InvalidTypeHint())
