from antidote._internal.utils.slots import SlotsRepr


class DummySlot(SlotsRepr):
    __slots__ = ('test', '__value')

    def __init__(self, test, value):
        self.test = test
        self.__value = value


def test_slot_repr_mixin():
    assert repr(DummySlot(1, 'test')) == "DummySlot(test=1, __value='test')"
