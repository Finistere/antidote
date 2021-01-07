import pytest


@pytest.mark.compiled_only
def test_fast_dict():
    from antidote.core.container import DependencyCache

    d = DependencyCache()
    n = 37
    for i in range(n):
        d[i] = i ** 2

    for i in range(n):
        assert d[i] == i ** 2

    assert len(d) == n
