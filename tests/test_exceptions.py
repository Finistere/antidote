from antidote import Tag
from antidote.exceptions import *


class Service:
    pass


def test_dependency_cycle_error():
    error = DependencyCycleError([Service, 'test', Service])

    service_info = f"{Service.__module__}.{Service.__name__}"

    for f in [str, repr]:
        assert service_info in f(error)
        assert "'test'" in f(error)


def test_dependency_not_found():
    o = object()
    error = DependencyNotFoundError(o)

    for f in [str, repr]:
        assert repr(o) in f(error)


def test_duplicate_dependency_error():
    dependency = object()
    existing_dependency = object()
    error = DuplicateDependencyError(dependency, existing_dependency)

    for f in [str, repr]:
        assert f(dependency) in f(error)
        assert f(existing_dependency) in f(error)

    message = "hello"
    error = DuplicateDependencyError(message)
    assert message in str(error)


def test_duplicate_tag_error():
    tag = Tag()
    dependency = object()

    error = DuplicateTagError(dependency, tag)
    assert str(tag) in str(error)
    assert str(dependency) in str(error)


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
