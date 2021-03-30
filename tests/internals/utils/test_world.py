import pytest

from antidote import world
from antidote._internal.world import new_container, LazyDependency
from antidote.core import Container


def test_new_container():
    assert isinstance(new_container(), Container)


def test_dependency():
    with world.test.empty():
        world.test.singleton('x', object())
        d = LazyDependency('x', object)
        assert d.unwrapped == 'x'
        assert d.get() is world.get('x')

    class A:
        pass

    with world.test.empty():
        world.test.singleton('a', A())
        world.test.singleton('x', object())

        assert LazyDependency('a', A).get() is world.get('a')

        with pytest.raises(TypeError):
            LazyDependency('x', A).get()
