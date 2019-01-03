import pytest

from antidote._internal.stack import DependencyStack
from antidote.exceptions import DependencyCycleError


class Service:
    pass


class CustomException(Exception):
    pass


def test_instantiating():
    ds = DependencyStack()

    with ds.instantiating(DependencyStack):
        with ds.instantiating('test'):
            pass

    with pytest.raises(DependencyCycleError):
        with ds.instantiating(DependencyStack):
            with ds.instantiating(DependencyStack):
                pass

    try:
        with ds.instantiating(DependencyStack):
            raise CustomException()
    except CustomException:
        pass

    # DependencyStack should be clean
    with ds.instantiating(DependencyStack):
        pass
