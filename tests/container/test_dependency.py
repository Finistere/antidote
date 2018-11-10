import pytest

from antidote import Dependency


class Service:
    pass


@pytest.mark.parametrize('id', ['test', 1, Service])
def test_eq_hash(id):
    p = Dependency(id)

    # does not fail
    hash(p)

    for f in (lambda e: e, hash):
        assert f(p) == f(p)

    assert repr(id) in repr(p)
