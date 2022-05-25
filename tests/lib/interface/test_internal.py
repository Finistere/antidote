import sys
from typing import Any, Optional, Union

import pytest

from antidote.lib.interface import Predicate, QualifiedBy
from antidote.lib.interface._internal import create_constraints as create

x = object()
y = object()


def test_create_constraints_qualifiers() -> None:
    assert create(QualifiedBy(x)) == create(qualified_by=[x])
    assert create(QualifiedBy(x)) == create(qualified_by=x)
    assert create(QualifiedBy(x, y)) == create(qualified_by=[x, y])
    assert create(QualifiedBy.one_of(x)) == create(qualified_by_one_of=[x])
    assert create(QualifiedBy.one_of(x, y)) == create(qualified_by_one_of=[x, y])

    assert create(QualifiedBy(x)) == [(QualifiedBy, QualifiedBy(x))]
    assert create(QualifiedBy.one_of(x)) == [(QualifiedBy, QualifiedBy.one_of(x))]


def test_create_invalid_kwargs() -> None:
    x = dict(x=1)
    with pytest.raises(TypeError, match="(?i).*Invalid qualifier.*"):
        create(qualified_by=x)

    with pytest.raises(TypeError, match="(?i).*qualified_by_one_of.*"):
        create(qualified_by_one_of=x)  # type: ignore

    with pytest.raises(TypeError, match="(?i).*Invalid qualifier.*"):
        create(qualified_by_one_of=[x])


def test_create_constraint_combination() -> None:
    assert create(QualifiedBy(x), QualifiedBy(x)) == create(QualifiedBy(x))
    assert create(QualifiedBy(x), QualifiedBy(y)) == create(QualifiedBy(x, y))
    assert set(create(QualifiedBy.one_of(x), QualifiedBy.one_of(y))) == {
        (QualifiedBy, QualifiedBy.one_of(x)),
        (QualifiedBy, QualifiedBy.one_of(y)),
    }


def test_create_constraint_invalid_predicate_class() -> None:
    with pytest.raises(TypeError, match="(?i).*PredicateConstraint.*"):
        create(object())  # type: ignore

    class MissingPredicateArgument:
        def evaluate(self, *args: object, **kwargs: object) -> None:
            ...

    with pytest.raises(TypeError, match="(?i).*predicate.*"):
        create(MissingPredicateArgument())  # type: ignore


@pytest.mark.parametrize(
    "type_hint",
    [Any, Union[int, float], Optional[int], Union[None, Predicate[Any], int], Predicate[Any]],
)
def test_create_constraint_invalid_type_hint(type_hint: Any) -> None:
    class InvalidTypeHint:
        def evaluate(self, predicate: type_hint) -> None:  # type: ignore
            ...

    with pytest.raises(TypeError, match="(?i).*Optional.*Predicate.*"):
        create(InvalidTypeHint())  # type: ignore


if sys.version_info >= (3, 10):

    def test_python310_support() -> None:
        class NewUnionSyntaxTypeHint:
            def evaluate(self, predicate: "QualifiedBy | None") -> bool:
                pass  # pragma: no cover

        create(NewUnionSyntaxTypeHint())
