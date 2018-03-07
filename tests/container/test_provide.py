import pytest

from antidote.container import Provide


class Service:
    pass


tests = [
    ('test', (1,), {}),
    (1, [], {'test': 1}),
    (Service, (1, 'test'), {'second': 'yes', 'another': 'no'}),
    (Service, [], {})
]


@pytest.mark.parametrize('dependency_id,args,kwargs', tests)
def test_eq_hash(dependency_id, args, kwargs):
    p = Provide(dependency_id, *args, **kwargs)

    for f in (lambda e: e, hash):
        assert (f(Provide(dependency_id, **kwargs)) == f(p)) is not len(args)
        assert (f(Provide(dependency_id, *args)) == f(p)) is not len(kwargs)
        assert (f(Provide(dependency_id)) == f(p)) is not (len(args)
                                                           or len(kwargs))
        assert (f(dependency_id) == f(p)) is not (len(args)
                                                  or len(kwargs))
