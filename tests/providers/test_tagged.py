from hypothesis import given, strategies as st

from antidote import Tag, Tagged


class Service:
    pass


@given(st.builds(Tagged, name=st.sampled_from(['test', '987 jkh@è'])))
def test_eq_hash(tagged):
    # does not fail
    hash(tagged)

    for f in (lambda e: e, hash):
        assert f(Tagged(tagged.name)) != f(tagged)

    assert repr(tagged.name) in repr(tagged)


def test_tag():
    t = Tag(name='test', val=1)

    assert 'test' == t.name
    assert 1 == t.val
    assert t.anything is None
