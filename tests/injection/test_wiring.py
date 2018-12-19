import pytest

from antidote.injection import wire


def test_invalid_value():
    with pytest.raises(ValueError):
        wire(object())

    with pytest.raises(ValueError):
        wire(1)

    with pytest.raises(ValueError):
        wire(lambda: None)
