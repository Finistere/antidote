import pytest

from antidote.exceptions import (DependencyCycleError, DependencyInstantiationError,
                                 DependencyNotFoundError, DuplicateDependencyError,
                                 FrozenWorldError)


class Service:
    pass


class LongRepr:
    def __repr__(self):
        return "\n'test'\n"


@pytest.mark.parametrize('error', [
    pytest.param(DependencyCycleError([Service, 'test', Service]), id='cycle'),
    pytest.param(DependencyCycleError([Service, LongRepr(), Service]), id='cycle-breaks'),
    pytest.param(DependencyInstantiationError(Service, ['test', Service]),
                 id='instantiation'),
    pytest.param(DependencyInstantiationError(Service, [LongRepr(), Service]),
                 id='instantiation-breaks'),
])
def test_stack_error(error):
    for f in [str, repr]:
        assert f"{Service.__module__}.{Service.__name__}" in f(error)
        assert "'test'" in f(error)


def test_dependency_not_found():
    o = object()
    error = DependencyNotFoundError(o)

    for f in [str, repr]:
        assert repr(o) in f(error)


def test_duplicate_dependency_error():
    message = "hello"
    error = DuplicateDependencyError(message)
    assert message in str(error)


def test_frozen_world():
    message = "my message"
    error = FrozenWorldError(message)
    assert message in str(error)
    assert message in repr(error)


def test_duplicate_dependency():
    x = object()
    y = object()
    error = DuplicateDependencyError(x, y)
    for f in [str, repr]:
        assert f(x) in f(error)
        assert f(y) in f(error)

    message = "test"
    error = DuplicateDependencyError(message)
    assert str(message) in str(error)
    assert str(message) in repr(error)
