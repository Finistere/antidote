import pytest

from antidote.container import DependencyStack, DependencyCycleError


class Service(object):
    pass


def test_format_stack():
    ds = DependencyStack([Service, 'test', 1, Service])
    service_info = "{}.{}".format(Service.__module__, Service.__name__)

    assert service_info in ds.format_stack()
    assert "'test'" in ds.format_stack()
    assert " 1 " in ds.format_stack()

    assert ds.format_stack() in repr(ds)


def test_instantiating():
    ds = DependencyStack()

    assert [] == list(ds)

    with ds.instantiating(DependencyStack):
        with ds.instantiating('test'):
            assert [DependencyStack, 'test'] == list(ds)

    assert [] == list(ds)

    with pytest.raises(DependencyCycleError):
        with ds.instantiating(DependencyStack):
            with ds.instantiating(DependencyStack):
                pass

    assert [] == list(ds)
