import antidote
import pytest


def test_set():
    o = object()
    antidote.set('auto_wire', o)
    assert antidote._manager.auto_wire is o

    with pytest.raises(ValueError):
        antidote.set('xxxx', None)
