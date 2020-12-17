import pytest

from antidote._internal.stack import DependencyStack
from antidote.exceptions import DependencyCycleError


class Service:
    pass


class CustomException(Exception):
    pass


def test_instantiating():
    stack = DependencyStack()
    a = object()
    b = object()

    with stack.instantiating(a):
        with stack.instantiating(b):
            pass

        # stack not have b anymore
        with stack.instantiating(b):
            pass

        with pytest.raises(DependencyCycleError):
            with stack.instantiating(a):
                pass

    # stack should be clean after cycle error
    with stack.instantiating(a):
        pass

    with pytest.raises(CustomException):
        with stack.instantiating(a):
            raise CustomException()

    # stack should be clean after user error
    with stack.instantiating(a):
        pass


def test_is_empty():
    stack = DependencyStack()
    a = object()
    b = object()

    assert stack.depth == 0

    with stack.instantiating(a):
        assert stack.depth == 1

        with stack.instantiating(b):
            assert stack.depth == 2

        assert stack.depth == 1

    assert stack.depth == 0


def test_to_list():
    stack = DependencyStack()
    a = object()
    b = object()

    assert stack.to_list() == []

    with stack.instantiating(a):
        assert stack.to_list() == [a]

        with stack.instantiating(b):
            assert stack.to_list() == [a, b]
            stack_copy = stack.to_list()
            stack_copy.append('dummy')
            # should not have impacted the actual stack
            assert stack.to_list() == [a, b]

        assert stack.to_list() == [a]

    assert stack.to_list() == []
