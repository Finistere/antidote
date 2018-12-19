import pytest

from antidote.container.stack import InstantiationStack
from antidote.exceptions import DependencyCycleError


class Service:
    pass


class CustomException(Exception):
    pass


def test_instantiating():
    ds = InstantiationStack()

    with ds.instantiating(InstantiationStack):
        with ds.instantiating('test'):
            pass

    with pytest.raises(DependencyCycleError):
        with ds.instantiating(InstantiationStack):
            with ds.instantiating(InstantiationStack):
                pass

    try:
        with ds.instantiating(InstantiationStack):
            raise CustomException()
    except CustomException:
        pass

    # InstantiationStack should be clean
    with ds.instantiating(InstantiationStack):
        pass
