from antidote import DependencyManager


def test_manager_repr():
    manager = DependencyManager()

    assert repr(manager.container) in repr(manager)
    assert repr(manager.injector) in repr(manager)
    assert 'auto_wire' in repr(manager)
    assert 'use_names' in repr(manager)
    assert 'mapping' in repr(manager)
