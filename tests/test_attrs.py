import pytest

from blood import ServiceManager


def test_attrs():
    manager = ServiceManager()
    container = manager.container

    try:
        import attr
    except ImportError:
        with pytest.raises(RuntimeError):
            manager.attrib()
        return

    @manager.register
    class Service(object):
        pass

    @attr.s
    class Test(object):
        service = manager.attrib(Service)

    test = Test()

    assert container[Service] is test.service

    @attr.s
    class BrokenTest(object):
        service = manager.attrib()

    with pytest.raises(ValueError):
        _ = BrokenTest()
