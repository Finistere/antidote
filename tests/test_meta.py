import os

from antidote import __version__, is_compiled


def test_is_compiled():
    assert isinstance(is_compiled(), bool)
    assert is_compiled() == (os.environ.get("ANTIDOTE_COMPILED") == "true")


def test_version():
    assert isinstance(__version__, str)
