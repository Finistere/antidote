from antidote import world
from antidote.core import LazyDependency, DependencyDebug, DependencyValue, Scope


def test_dependency():
    with world.test.empty():
        world.test.singleton('x', object())
        d = LazyDependency('x')
        assert d.unwrapped == 'x'
        assert d.get() is world.get('x')


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


def test_dependency_hash_eq():
    d1 = LazyDependency('same')
    d2 = LazyDependency('same')
    x = LazyDependency('different')

    assert hash(d1) == hash(d2)
    assert d1 == d2

    assert hash(d1) != hash(x)
    assert d1 != x
