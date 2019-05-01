from antidote.exceptions import (DependencyCycleError, DependencyNotFoundError,
                                 DuplicateDependencyError)


class Service:
    pass


def test_dependency_cycle_error():
    error = DependencyCycleError([Service, 'test', 1, Service])

    service_info = "{}.{}".format(Service.__module__, Service.__name__)

    for f in [str, repr]:
        assert service_info in f(error)
        assert "'test'" in f(error)
        assert " 1 " in f(error)


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
