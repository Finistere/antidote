from antidote._internal import state


def test_double_init():
    state.init()
    state.init()
