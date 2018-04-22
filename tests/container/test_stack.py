import pytest

from antidote.container import DependencyCycleError, InstantiationStack


class Service(object):
    pass


def test_format_stack():
    ds = InstantiationStack([Service, 'test', 1, Service])
    service_info = "{}.{}".format(Service.__module__, Service.__name__)

    assert service_info in ds.format_stack()
    assert "'test'" in ds.format_stack()
    assert " 1 " in ds.format_stack()

    assert ds.format_stack() in repr(ds)


def test_instantiating():
    ds = InstantiationStack()

    assert [] == list(ds)

    with ds.instantiating(InstantiationStack):
        with ds.instantiating('test'):
            assert [InstantiationStack, 'test'] == list(ds)

    assert [] == list(ds)

    with pytest.raises(DependencyCycleError):
        with ds.instantiating(InstantiationStack):
            with ds.instantiating(InstantiationStack):
                pass

    assert [] == list(ds)

    class CustomException(Exception):
        pass

    try:
        with ds.instantiating(InstantiationStack):
            raise CustomException()
    except CustomException:
        pass

    assert [] == list(ds)
