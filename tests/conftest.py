import pytest

from antidote import is_compiled


def pytest_runtest_setup(item):
    if any(mark.name == "compiled_only" for mark in item.iter_markers()):
        if not is_compiled():
            pytest.skip("Compiled only test.")
