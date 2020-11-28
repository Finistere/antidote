import pytest

from antidote._internal.utils import SlotRecord
from antidote._internal.utils.slots import SlotsRepr


class DummySlot(SlotsRepr):
    __slots__ = ('test', '__value')

    def __init__(self, test, value):
        self.test = test
        self.__value = value


def test_slot_repr_mixin():
    assert repr(DummySlot(1, 'test')) == "DummySlot(test=1, __value='test')"


@pytest.mark.parametrize('cls', [SlotRecord])
def test_copy(cls):
    class A(cls):
        __slots__ = ('x', 'y')

        def __init__(self, x, y):
            super().__init__(x=x, y=y)

    a = A(1, 2)
    assert (a.x, a.y) == (1, 2)  # Sanity check

    b = a.copy()
    assert b is not a
    assert (b.x, b.y) == (1, 2)

    c = a.copy(x=10)
    assert (c.x, c.y) == (10, 2)

    d = a.copy(y=20)
    assert (d.x, d.y) == (1, 20)

    e = a.copy(x=10, y=20)
    assert (e.x, e.y) == (10, 20)
