import os

from antidote.utils import is_compiled


def test_is_compiled():
    assert isinstance(is_compiled(), bool)
    if 'ANTIDOTE_COMPILED' in os.environ:
        assert is_compiled() == (os.environ["ANTIDOTE_COMPILED"] == "1")
