from antidote import DependencyManager


def test_manager_repr():
    manager = DependencyManager()

    assert repr(manager.container) in repr(manager)
    assert repr(manager.injector) in repr(manager)
    assert 'auto_wire' in repr(manager)
    assert 'use_names' in repr(manager)
    assert 'mapping' in repr(manager)


def test_provide():
    manager = DependencyManager()
    manager.container['test'] = object()

    @manager.register
    class Service:
        def __init__(self, name):
            self.name = name

    assert manager.container['test'] == manager.provide('test')

    s = manager.provide(Service, name='test')
    assert isinstance(s, Service)
    assert 'test' == s.name
