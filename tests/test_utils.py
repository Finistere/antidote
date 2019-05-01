from antidote.utils import is_compiled


def test_is_compiled():
    assert isinstance(is_compiled(), bool)
