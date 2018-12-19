import pytest
from hypothesis import given, strategies as st

from antidote import Tag, Tagged


class Service:
    pass


@given(st.builds(
    Tagged,
    name=st.sampled_from(['test', '987 jkh@è']),
    filter=st.sampled_from([None, lambda t: t.valid is True])
))
def test_eq_hash(tagged):
    # does not fail
    hash(tagged)

    for f in (lambda e: e, hash):
        assert f(Tagged(tagged.name, tagged.filter)) != f(tagged)

    assert repr(tagged.name) in repr(tagged)
    assert repr(tagged.filter) in repr(tagged)


@pytest.mark.parametrize(
    'filter',
    [None, lambda t: t.valid is True]
)
def test_filter(filter):
    tagged = Tagged('', filter=filter)
    assert tagged.filter(Tag('anything', valid=True))
    assert tagged.filter(Tag('something else', valid=True))

    if filter is not None:
        assert not tagged.filter(Tag('anything', valid=False))
        assert not tagged.filter(Tag('anything'))
    else:
        assert tagged.filter(Tag('anything', valid=False))
        assert tagged.filter(Tag('anything'))


def test_invalid_filter():
    with pytest.raises(ValueError):
        Tagged('', filter='test')


def test_tag():
    t = Tag(name='test', val=1)

    assert 'test' == t.name
    assert 1 == t.val
    assert t.anything is None
