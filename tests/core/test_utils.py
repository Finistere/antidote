import pytest

from antidote import world
from antidote.core import LazyDependency, DependencyDebug, DependencyValue, Scope


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


def test_dependency_instance():
    ref = DependencyValue("test", scope=Scope.singleton())
    assert ref == DependencyValue("test", scope=Scope.singleton())
    assert ref != DependencyValue("test2", scope=Scope.singleton())
    assert ref != DependencyValue("test", scope=None)


def test_dependency_debug():
    ref = DependencyDebug("info",
                          scope=Scope.singleton(),
                          wired=[1],
                          dependencies=[2])
    assert ref == DependencyDebug("info",
                                  scope=Scope.singleton(),
                                  wired=[1],
                                  dependencies=[2])
    assert ref != DependencyDebug("info2",
                                  scope=Scope.singleton(),
                                  wired=[1],
                                  dependencies=[2])
    assert ref != DependencyDebug("info",
                                  scope=None,
                                  wired=[1],
                                  dependencies=[2])
    assert ref != DependencyDebug("info",
                                  scope=Scope.singleton(),
                                  wired=[10],
                                  dependencies=[2])
    assert ref != DependencyDebug("info",
                                  scope=Scope.singleton(),
                                  wired=[1],
                                  dependencies=[20])
