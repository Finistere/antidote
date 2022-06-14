import pytest

from antidote import config


def test_invalid_auto_detect_type_hints_locals() -> None:
    with pytest.raises(TypeError, match=".*auto_detect_type_hints_locals.*"):
        config.auto_detect_type_hints_locals = "auto"  # type: ignore
