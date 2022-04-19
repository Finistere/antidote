import pytest

from antidote import config, is_compiled

config.auto_detect_type_hints_locals = True


def pytest_runtest_setup(item):
    if any(mark.name == "compiled_only" for mark in item.iter_markers()):
        if not is_compiled():
            pytest.skip("Compiled only test.")
