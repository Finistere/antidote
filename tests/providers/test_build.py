import pytest

from antidote import Build


class Service:
    pass


@pytest.mark.parametrize(
    'wrapped,args,kwargs',
    [
        ('test', (1,), {}),
        (1, tuple(), {'test': 1}),
        (Service, (1, 'test'), {'another': 'no'}),
        (Service, tuple(), {'not_hashable': {'hey': 'hey'}})
    ]
)
def test_eq_hash(wrapped, args, kwargs):
    b = Build(wrapped, *args, **kwargs)

    # does not fail
    hash(b)

    for f in (lambda e: e, hash):
        assert f(Build(wrapped, *args, **kwargs)) == f(b)

    assert repr(wrapped) in repr(b)
    if args or kwargs:
        assert repr(args) in repr(b)
        assert repr(kwargs) in repr(b)


def test_invalid_build():
    with pytest.raises(TypeError):
        Build(1)

    with pytest.raises(TypeError):
        Build()
