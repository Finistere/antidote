import pytest

from antidote.container import DependencyStack, DependencyCycleError


class Service(object):
    pass


stack = [DependencyStack, 'test', Service, 1, Service]


@pytest.mark.parametrize(
    '_str,obj',
    [
        (str, DependencyStack(stack)),
        (repr, DependencyStack(stack)),
        (str, DependencyCycleError(DependencyStack(stack))),
    ]
)
def test_repr(_str, obj):
    assert "tests.test_dependency_stack.Service" in _str(obj)
    assert "antidote.container.DependencyStack" in _str(obj)
    assert "'test'" in _str(obj)
    assert " 1 " in _str(obj)


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

