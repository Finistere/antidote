import pytest

from antidote import Build


class Service:
    pass


@pytest.mark.parametrize(
    'id,args,kwargs',
    [
        ('test', (1,), {}),
        (1, tuple(), {'test': 1}),
        (Service, (1, 'test'), {'another': 'no'}),
        (Service, tuple(), {}),
        (Service, tuple(), {'not_hashable': {'hey': 'hey'}})
    ]
)
def test_eq_hash(id, args, kwargs):
    p = Build(id, *args, **kwargs)

    # does not fail
    hash(p)

    for f in (lambda e: e, hash):
        assert (f(Build(id, **kwargs)) == f(p)) is not len(args)
        assert (f(Build(id, *args)) == f(p)) is not len(kwargs)
        assert (f(Build(id)) == f(p)) is not (len(args) or len(kwargs))
        assert (f(id) == f(p)) is not (len(args) or len(kwargs))

    assert repr(id) in repr(p)
    assert repr(args) in repr(p)
    assert repr(kwargs) in repr(p)
