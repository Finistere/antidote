import pytest

from antidote import Prepare


class Service:
    pass


tests = [
    ('test', (1,), {}),
    (1, tuple(), {'test': 1}),
    (Service, (1, 'test'), {'another': 'no'}),
    (Service, tuple(), {})
]


@pytest.mark.parametrize('dependency_id,args,kwargs', tests)
def test_eq_hash(dependency_id, args, kwargs):
    p = Prepare(dependency_id, *args, **kwargs)

    for f in (lambda e: e, hash):
        assert (f(Prepare(dependency_id, **kwargs)) == f(p)) is not len(args)
        assert (f(Prepare(dependency_id, *args)) == f(p)) is not len(kwargs)
        assert (f(Prepare(dependency_id)) == f(p)) is not (len(args)
                                                           or len(kwargs))
        assert (f(dependency_id) == f(p)) is not (len(args)
                                                  or len(kwargs))

    assert repr(dependency_id) in repr(p)
    assert repr(args) in repr(p)
    assert repr(kwargs) in repr(p)
