from antidote import DependencyCycleError


class Service:
    pass


def test_dependency_cycle_error():
    error = DependencyCycleError([Service, 'test', 1, Service])

    service_info = "{}.{}".format(Service.__module__, Service.__name__)

    assert service_info in repr(error)
    assert "'test'" in repr(error)
    assert " 1 " in repr(error)
