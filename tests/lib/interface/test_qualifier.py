import itertools
from typing import List

import pytest

from antidote import QualifiedBy

x = object()
y = object()
z = object()


def test_qualified_by_must_have_at_least_one_qualifier() -> None:
    with pytest.raises(ValueError, match="(?i).*at least one qualifier.*"):
        QualifiedBy()


@pytest.mark.parametrize('qualifiers', [
    pytest.param([1], id='int'),
    pytest.param([1.123], id='float'),
    pytest.param([complex(1)], id='complex'),
    pytest.param([True], id='bool'),
    pytest.param([b''], id='bytes'),
    pytest.param([bytearray()], id='bytearray'),
    pytest.param(["hello"], id='str'),
    pytest.param([[object()]], id='list'),
    pytest.param([{object(): object()}], id='dict'),
    pytest.param([{object()}], id='set'),
    pytest.param([(object(),)], id='tuple'),
    pytest.param([object(), 2], id='mixed')
])
def test_qualifier_validation(qualifiers: List[object]) -> None:
    with pytest.raises(TypeError, match="(?i).*qualifier.*"):
        QualifiedBy(*qualifiers)

    with pytest.raises(TypeError, match="(?i).*qualifier.*"):
        QualifiedBy.one_of(*qualifiers)


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
    assert QualifiedBy(x).evaluate(QualifiedBy(x))
    assert QualifiedBy(x, y).evaluate(QualifiedBy(x, y))
    assert QualifiedBy(x, y).evaluate(QualifiedBy(y, x))
    assert QualifiedBy(x).evaluate(QualifiedBy(x, y))
    assert QualifiedBy(y).evaluate(QualifiedBy(x, y))

    assert not QualifiedBy(x).evaluate(QualifiedBy(y))
    assert not QualifiedBy(x, y).evaluate(QualifiedBy(x))

    # on missing QualifiedBy
    assert not QualifiedBy(x).evaluate(None)


def test_qualified_by_one_of() -> None:
    assert QualifiedBy.one_of(x).evaluate(QualifiedBy(x))
    assert QualifiedBy.one_of(x).evaluate(QualifiedBy(x, y))

    assert QualifiedBy.one_of(x, y).evaluate(QualifiedBy(x))
    assert QualifiedBy.one_of(x, y).evaluate(QualifiedBy(x, y))
    assert QualifiedBy.one_of(x, y).evaluate(QualifiedBy(y))

    # Ensuring (roughly) we have all cases of ordering with id()
    for left in itertools.permutations([x, y, z]):
        for right in [x, y, z]:
            QualifiedBy.one_of(*left).evaluate(QualifiedBy(object(), right, object()))

    assert not QualifiedBy.one_of(x).evaluate(QualifiedBy(y))

    # on missing QualifiedBy
    assert not QualifiedBy.one_of(x).evaluate(None)


def test_only_qualifier_id_matters() -> None:
    assert QualifiedBy(x, x) == QualifiedBy(x)

    class Dummy:
        def __init__(self, name: str) -> None:
            self.name = name

        def __eq__(self, other: object) -> bool:
            return isinstance(other, Dummy)

        def __hash__(self) -> int:
            return hash(Dummy)  # pragma: no cover

        def __repr__(self) -> str:
            return f"Dummy({self.name})"  # pragma: no cover

    a = Dummy('a')
    b = Dummy('b')
    assert a == b

    assert QualifiedBy(a) != QualifiedBy(b)
    assert QualifiedBy(a, b) != QualifiedBy(a)
    assert QualifiedBy(a, b) != QualifiedBy(b)

    assert not QualifiedBy(b).evaluate(QualifiedBy(a))
    assert not QualifiedBy.one_of(b).evaluate(QualifiedBy(a))
