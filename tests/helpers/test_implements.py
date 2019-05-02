from enum import Enum

import pytest

from antidote import implements, register
from antidote.core import DependencyContainer
from antidote.providers import IndirectProvider, FactoryProvider


@pytest.fixture()
def container():
    c = DependencyContainer()
    c.register_provider(FactoryProvider(container=c))
    c.register_provider(IndirectProvider(container=c))

    return c


class IService:
    pass


class Profile(Enum):
    A = 'A'
    B = 'B'


def test_implements(container: DependencyContainer):
    @implements(IService, container=container)
    @register(container=container)
    class Service(IService):
        pass

    assert container.get(IService) is container.get(Service)


def test_implements_profile(container: DependencyContainer):
    @implements(IService, state=Profile.A, container=container)
    @register(container=container)
    class ServiceA(IService):
        pass

    @implements(IService, state=Profile.B, container=container)
    @register(container=container)
    class ServiceB(IService):
        pass

    container.update_singletons({Profile: Profile.A})
    assert container.get(IService) is container.get(ServiceA)


def test_invalid_implements(container: DependencyContainer):
    with pytest.raises(TypeError):
        @implements(IService, container=container)
        class A:
            pass

    with pytest.raises(TypeError):
        implements(IService, container=container)(1)
