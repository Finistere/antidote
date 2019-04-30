from enum import auto, Flag

import pytest

from antidote import implements, register
from antidote.core import DependencyContainer
from antidote.providers import InterfaceProvider, ServiceProvider


@pytest.fixture()
def container():
    c = DependencyContainer()
    c.register_provider(ServiceProvider(container=c))
    c.register_provider(InterfaceProvider(container=c))

    return c


class IService:
    pass


class Profile(Flag):
    A = auto()
    B = auto()


def test_implements(container: DependencyContainer):
    @implements(IService, container=container)
    @register(container=container)
    class Service(IService):
        pass

    assert container.get(IService) is container.get(Service)


def test_implements_profile(container: DependencyContainer):
    @implements(IService, profile=Profile.A, container=container)
    @register(container=container)
    class ServiceA(IService):
        pass

    @implements(IService, profile=Profile.B, container=container)
    @register(container=container)
    class ServiceB(IService):
        pass

    container.update_singletons({Profile: Profile.A})
    assert container.get(IService) is container.get(ServiceA)
