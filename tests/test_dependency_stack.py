import pytest

from antidote.container import DependencyStack, DependencyCycleError


class Service(object):
    pass


def test_format_stack():
    ds = DependencyStack([DependencyStack, 'test', Service, 1, Service])
    assert "tests.test_dependency_stack.Service" in ds.format_stack()
    assert "antidote.container.DependencyStack" in ds.format_stack()
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

