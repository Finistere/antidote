import pytest

from antidote import world
from antidote.core import DependencyContainer
from antidote.core.exceptions import DuplicateDependencyError, FrozenWorldError
from antidote.providers.factory import FactoryProvider
from antidote.providers.indirect import IndirectProvider


@pytest.fixture(autouse=True)
def empty_world():
    with world.test.empty():
        yield


@pytest.fixture
def factory():
    provider = FactoryProvider()
    world.get(DependencyContainer).register_provider(provider)
    return provider


@pytest.fixture
def indirect():
    provider = IndirectProvider()
    world.get(DependencyContainer).register_provider(provider)
    return provider


class IService:
    pass


class Service(IService):
    pass


class ServiceA(IService):
    pass


class ServiceB(IService):
    pass


def test_none(indirect: IndirectProvider):
    assert indirect.world_provide(IService) is None


def test_simple(indirect: IndirectProvider,
                factory: FactoryProvider):
    factory.register_class(Service)
    indirect.register_static(IService, Service)

    assert indirect.world_provide(IService).instance is world.get(Service)
    assert indirect.world_provide(IService).singleton is True
    assert str(IService) in repr(indirect)


def test_not_singleton_interface(indirect: IndirectProvider,
                                 factory: FactoryProvider):
    factory.register_class(Service, singleton=False)
    indirect.register_static(IService, Service)

    service = world.get(Service)
    assert indirect.world_provide(IService).instance is not service
    assert isinstance(indirect.world_provide(IService).instance, Service)
    assert indirect.world_provide(IService).singleton is False


@pytest.mark.parametrize('singleton,static',
                         [(True, True), (True, False), (False, True), (False, False)])
def test_implementation_static_singleton(indirect: IndirectProvider,
                                         factory: FactoryProvider,
                                         singleton: bool, static: bool):
    choice = 'a'

    def implementation():
        return dict(a=ServiceA, b=ServiceB)[choice]

    factory.register_class(ServiceA, singleton=singleton)
    factory.register_class(ServiceB, singleton=singleton)
    indirect.register_link(IService, linker=implementation, static=static)

    assert (indirect.world_provide(IService).instance is world.get(
        ServiceA)) is singleton
    assert isinstance(indirect.world_provide(IService).instance, ServiceA)
    assert indirect.world_provide(IService).singleton is (singleton and static)

    choice = 'b'
    assert implementation() == ServiceB
    assert indirect.world_provide(IService).singleton is (singleton and static)
    if static:
        assert (indirect.world_provide(IService).instance is world.get(
            ServiceA)) is singleton
        assert isinstance(indirect.world_provide(IService).instance, ServiceA)
    else:
        assert (indirect.world_provide(IService).instance is world.get(
            ServiceB)) is singleton
        assert isinstance(indirect.world_provide(IService).instance, ServiceB)


def test_clone(indirect: IndirectProvider, factory: FactoryProvider):
    class IService2:
        pass

    class Service2(IService2):
        pass

    factory.register_class(Service2)
    factory.register_class(Service)

    indirect.register_link(IService, lambda: Service, static=False)
    indirect.register_static(IService2, Service2)

    clone = indirect.clone()
    assert clone.world_provide(IService).instance is world.get(Service)
    assert clone.world_provide(IService2).instance is world.get(Service2)

    class IService3:
        pass

    class Service3(IService3):
        pass

    factory.register_class(Service3)
    clone.register_static(IService3, Service3)
    assert clone.world_provide(IService3).instance is world.get(Service3)
    assert indirect.world_provide(IService3) is None


def test_freeze(indirect: IndirectProvider):
    indirect.freeze()

    with pytest.raises(FrozenWorldError):
        indirect.register_link(IService, lambda: Service, static=False)

    with pytest.raises(FrozenWorldError):
        indirect.register_static(IService, Service)

    assert indirect.world_provide(IService) is None


def test_register_static_duplicate_check(indirect: IndirectProvider):
    indirect.register_static(IService, Service)

    with pytest.raises(DuplicateDependencyError):
        indirect.register_static(IService, Service)

    with pytest.raises(DuplicateDependencyError):
        indirect.register_link(IService, lambda: Service)


def test_register_duplicate_check(indirect: IndirectProvider):
    indirect.register_link(IService, lambda: Service)

    with pytest.raises(DuplicateDependencyError):
        indirect.register_static(IService, Service)

    with pytest.raises(DuplicateDependencyError):
        indirect.register_link(IService, lambda: Service)
