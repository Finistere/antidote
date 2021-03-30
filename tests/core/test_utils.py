from antidote.core import DependencyDebug, DependencyValue, Scope


def test_dependency_value():
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
