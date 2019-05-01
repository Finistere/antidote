from enum import auto, Flag

import pytest

from antidote.core import DependencyContainer
from antidote.exceptions import DuplicateDependencyError, UndefinedContextError
from antidote.providers.indirect import IndirectProvider
from antidote.providers.service import ServiceProvider


@pytest.fixture
def container():
    return DependencyContainer()


@pytest.fixture
def service_provider(container):
    provider = ServiceProvider(container=container)
    container.register_provider(provider)
    return provider


@pytest.fixture
def interface_provider(container):
    provider = IndirectProvider(container=container)
    container.register_provider(provider)
    return provider


class IService:
    pass


class Service(IService):
    pass


class ServiceA(IService):
    pass


class ServiceB(IService):
    pass


class Profile(Flag):
    A = auto()
    B = auto()


def test_none(interface_provider: IndirectProvider):
    assert interface_provider.provide(IService) is None


def test_interface(container: DependencyContainer,
                   interface_provider: IndirectProvider,
                   service_provider: ServiceProvider):
    service_provider.register(Service)
    interface_provider.register(IService, Service)

    expected = container.get(Service)
    assert interface_provider.provide(IService).instance is expected
    assert interface_provider.provide(IService).singleton is True


def test_not_singleton_interface(container: DependencyContainer,
                                 interface_provider: IndirectProvider,
                                 service_provider: ServiceProvider):
    service_provider.register(Service, singleton=False)
    interface_provider.register(IService, Service)

    service = container.get(Service)
    assert interface_provider.provide(IService).instance is not service
    assert isinstance(interface_provider.provide(IService).instance, Service)
    assert interface_provider.provide(IService).singleton is False


def test_profile_instance(container: DependencyContainer,
                          interface_provider: IndirectProvider,
                          service_provider: ServiceProvider):
    service_provider.register(ServiceA)
    service_provider.register(ServiceB, singleton=False)
    interface_provider.register(IService, ServiceA, Profile.A)
    interface_provider.register(IService, ServiceB, Profile.B)
    current_profile = Profile.A

    def get_profile():
        return current_profile

    service_provider.register(Profile, singleton=False, factory=get_profile)

    service_a = container.get(ServiceA)
    service_b = container.get(ServiceB)

    assert service_a is interface_provider.provide(IService).instance
    assert interface_provider.provide(IService).singleton is False

    current_profile = Profile.B
    assert service_b is not interface_provider.provide(IService).instance
    assert isinstance(interface_provider.provide(IService).instance, ServiceB)
    assert interface_provider.provide(IService).singleton is False


def test_singleton_profile_instance(container: DependencyContainer,
                                    interface_provider: IndirectProvider,
                                    service_provider: ServiceProvider):
    service_provider.register(ServiceA)
    service_provider.register(ServiceB, singleton=False)
    interface_provider.register(IService, ServiceA, Profile.A)
    interface_provider.register(IService, ServiceB, Profile.B)

    service_a = container.get(ServiceA)

    container.update_singletons({Profile: Profile.A})
    assert service_a is interface_provider.provide(IService).instance
    assert interface_provider.provide(IService).singleton is True


def test_singleton_profile_instance_2(container: DependencyContainer,
                                      interface_provider: IndirectProvider,
                                      service_provider: ServiceProvider):
    service_provider.register(ServiceA)
    service_provider.register(ServiceB, singleton=False)
    interface_provider.register(IService, ServiceA, Profile.A)
    interface_provider.register(IService, ServiceB, Profile.B)

    service_b = container.get(ServiceB)

    container.update_singletons({Profile: Profile.B})
    assert service_b is not interface_provider.provide(IService).instance
    assert isinstance(interface_provider.provide(IService).instance, ServiceB)
    assert interface_provider.provide(IService).singleton is False


def test_multi_profile_instance(container: DependencyContainer,
                                interface_provider: IndirectProvider,
                                service_provider: ServiceProvider):
    service_provider.register(ServiceA)
    interface_provider.register(IService, ServiceA, Profile.A | Profile.B)
    service_a = container.get(ServiceA)
    current_profile = Profile.A

    def get_profile():
        return current_profile

    service_provider.register(Profile, singleton=False, factory=get_profile)

    assert service_a is interface_provider.provide(IService).instance
    assert interface_provider.provide(IService).singleton is False

    current_profile = Profile.B
    assert service_a is interface_provider.provide(IService).instance
    assert interface_provider.provide(IService).singleton is False


def test_invalid_profile(interface_provider: IndirectProvider):
    with pytest.raises(TypeError):
        interface_provider.register(IService, Service, 1)


@pytest.mark.parametrize(
    'first,second',
    [
        ((ServiceA,), (ServiceB,)),
        ((ServiceA,), (ServiceB, Profile.B)),
        ((ServiceA, Profile.A), (ServiceB,)),
        ((ServiceA, Profile.A), (ServiceB, Profile.A)),
    ]
)
def test_duplicate(interface_provider: IndirectProvider, first: tuple, second: tuple):
    interface_provider.register(IService, *first)

    with pytest.raises(DuplicateDependencyError, match=str(IService)):
        interface_provider.register(IService, *second)


def test_undefined_context(container: DependencyContainer,
                           interface_provider: IndirectProvider,
                           service_provider: ServiceProvider):
    service_provider.register(ServiceA)
    service_provider.register(ServiceB)
    interface_provider.register(IService, ServiceA, Profile.A)
    container.update_singletons({Profile: Profile.B})

    with pytest.raises(UndefinedContextError):
        interface_provider.provide(IService)
