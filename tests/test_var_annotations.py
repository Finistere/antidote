from antidote import register, new_container, attrib


def test_attrs():
    container = new_container()

    try:
        import attr
    except ImportError:
        return

    @register(container=container)
    class Service:
        pass

    @attr.s
    class Test:
        service: Service = attrib(container=container)

    test = Test()

    assert container[Service] is test.service
