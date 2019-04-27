from antidote._internal.utils import SlotsReprMixin, is_compiled


class DummySlot(SlotsReprMixin):
    __slots__ = ('test', 'value')

    def __init__(self, test, value):
        self.test = test
        self.value = value


def test_slot_repr_mixin():
    assert repr(DummySlot(1, 'test')) == "DummySlot(test=1, value='test')"


def test_is_compiled():
    is_compiled()
