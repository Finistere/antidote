import pytest

from antidote.exceptions import (
    DependencyDuplicateError, DependencyNotProvidableError
)
from antidote.providers.factories import DependencyFactories


class Service(object):
    def __init__(self, *args):
        pass


class ServiceSubclass(Service):
    pass


class AnotherService(object):
    def __init__(self, *args):
        pass


def test_register():
    provider = DependencyFactories()
    provider.register(Service, Service)

    dependency = provider.__antidote_provide__(Service)
    assert isinstance(dependency.instance, Service)


def test_register_factory_id():
    provider = DependencyFactories()
    provider.register(Service, lambda: Service())

    dependency = provider.__antidote_provide__(Service)
    assert isinstance(dependency.instance, Service)


def test_singleton():
    provider = DependencyFactories()
    provider.register(Service, Service, singleton=True)
    provider.register(AnotherService, AnotherService, singleton=False)

    assert provider.__antidote_provide__(Service).singleton is True
    assert provider.__antidote_provide__(AnotherService).singleton is False


def test_register_for_subclasses():
    provider = DependencyFactories()
    provider.register(Service, lambda cls: cls(), build_subclasses=True)

    assert isinstance(
        provider.__antidote_provide__(Service).instance,
        Service
    )
    assert isinstance(
        provider.__antidote_provide__(ServiceSubclass).instance,
        Service
    )

    with pytest.raises(DependencyNotProvidableError):
        provider.__antidote_provide__(AnotherService)


def test_register_not_callable_error():
    provider = DependencyFactories()

    with pytest.raises(ValueError):
        provider.register(1, 1)


def test_register_id_null():
    provider = DependencyFactories()

    with pytest.raises(ValueError):
        provider.register(None, Service)


def test_duplicate_error():
    provider = DependencyFactories()
    provider.register(Service, Service)

    with pytest.raises(DependencyDuplicateError):
        provider.register(Service, Service)

    with pytest.raises(DependencyDuplicateError):
        provider.register(Service, lambda: Service())
