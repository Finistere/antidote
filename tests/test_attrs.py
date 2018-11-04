import pytest

from antidote import DependencyManager


def test_attrs():
    manager = DependencyManager()
    container = manager.container

    try:
        import attr
    except ImportError:
        with pytest.raises(RuntimeError):
            manager.attrib()
        return

    @manager.register
    class Service:
        pass

    container['parameter'] = object()

    @attr.s
    class Test:
        service = manager.attrib(Service)
        parameter = manager.attrib(use_name=True)

    test = Test()

    assert container[Service] is test.service
    assert container['parameter'] is test.parameter

    @attr.s
    class BrokenTest:
        service = manager.attrib()

    with pytest.raises(ValueError):
        BrokenTest()
