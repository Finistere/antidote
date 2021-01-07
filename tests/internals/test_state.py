import pytest

from antidote._internal import state


def test_double_init():
    state.init()
    state.init()
    assert state.current_container() is not None


def test_reset():
    state.reset()
    with pytest.raises(AssertionError):
        state.current_container()

    state.init()
    assert state.current_container() is not None


def test_overridable_container():
    with pytest.raises(RuntimeError):
        state.current_overridable_container()
