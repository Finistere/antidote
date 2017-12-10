from antidote import DependencyManager


def test_attrs():
    manager = DependencyManager()
    container = manager.container

    try:
        import attr
    except ImportError:
        return

    @manager.register
    class Service(object):
        pass

    @attr.s
    class Test(object):
        service: Service = manager.attrib()

    test = Test()

    assert container[Service] is test.service
