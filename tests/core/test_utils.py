from antidote import world
from antidote.core import Dependency, DependencyInstance
from antidote.core.utils import DependencyDebug


def test_dependency():
    with world.test.empty():
        world.singletons.add('x', object())
        d = Dependency('x')
        assert d.value == 'x'
        assert d.get() is world.get('x')


def test_dependency_instance():
    ref = DependencyInstance("test", singleton=True)
    assert ref == DependencyInstance("test", singleton=True)
    assert ref != DependencyInstance("test2", singleton=True)
    assert ref != DependencyInstance("test", singleton=False)


def test_dependency_debug():
    ref = DependencyDebug(info="info", singleton=True, wired=[1], dependencies=[2])
    assert ref == DependencyDebug(info="info", singleton=True, wired=[1],
                                  dependencies=[2])
    assert ref != DependencyDebug(info="info2", singleton=True, wired=[1],
                                  dependencies=[2])
    assert ref != DependencyDebug(info="info", singleton=False, wired=[1],
                                  dependencies=[2])
    assert ref != DependencyDebug(info="info", singleton=True, wired=[10],
                                  dependencies=[2])
    assert ref != DependencyDebug(info="info", singleton=True, wired=[1],
                                  dependencies=[20])


def test_dependency_hash_eq():
    d1 = Dependency('same')
    d2 = Dependency('same')
    x = Dependency('different')

    assert hash(d1) == hash(d2)
    assert d1 == d2

    assert hash(d1) != hash(x)
    assert d1 != x
