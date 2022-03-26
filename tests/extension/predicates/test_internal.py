from antidote.extension.predicates import QualifiedBy
from antidote.extension.predicates._internal import create_constraints

x = object()
y = object()


def test_create_constraints_qualified_by():
    assert create_constraints(QualifiedBy(x)) == [(QualifiedBy, QualifiedBy(x))]
    assert create_constraints(qualified_by=[x]) == [(QualifiedBy, QualifiedBy(x))]
    assert create_constraints(QualifiedBy(x), qualified_by=[x]) == [(QualifiedBy, QualifiedBy(x))]
    assert create_constraints(QualifiedBy(x), qualified_by=[y]) \
           == [(QualifiedBy, QualifiedBy(x, y))]
