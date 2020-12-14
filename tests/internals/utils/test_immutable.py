import pytest

from antidote._internal.utils.immutable import FinalImmutable, Immutable


@pytest.fixture(params=[Immutable, FinalImmutable])
def cls(request):
    return request.param


def test_immutable_meta(cls: type):
    class A(cls):
        __slots__ = ('value',)

    class B(cls):
        __slots__ = ('value',)

        def __init__(self, x):  # Should have a value argument or override copy()
            pass

        def copy(self):
            pass


def test_invalid_immutable(cls: type):
    with pytest.raises(TypeError, match=".*slots.*"):
        class A(cls):
            pass

    with pytest.raises(ValueError, match="(?i).*private.*"):
        class B(cls):
            __slots__ = ('__value',)


def test_immutability(cls: type):
    class A(cls):
        __slots__ = ('x', 'y')

        def __init__(self, x, y):
            super().__init__(x=x, y=y)

    x = object()
    y = object()

    a = A(x, y)
    assert a.x is x
    assert a.y is y

    with pytest.raises(AttributeError):
        a.x = 1

    with pytest.raises(AttributeError):
        a.unknown = 1
