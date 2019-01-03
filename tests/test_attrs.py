import pytest

from antidote import attrib, new_container


class Service:
    pass


@pytest.fixture()
def container():
    c = new_container()
    c.update_singletons({Service: Service(), 'parameter': object()})

    return c


try:
    import attr
except ImportError:
    def test_runtime_error():
        with pytest.raises(RuntimeError):
            attrib()
else:
    def test_simple(container):
        @attr.s
        class Test:
            service = attrib(Service, container=container)
            parameter = attrib(use_name=True, container=container)

        test = Test()

        assert container[Service] is test.service
        assert container['parameter'] is test.parameter

    def test_invalid_attrib(container):
        @attr.s
        class BrokenTest:
            service = attrib(container=container)

        with pytest.raises(RuntimeError):
            BrokenTest()
