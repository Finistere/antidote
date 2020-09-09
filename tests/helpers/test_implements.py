import pytest

from antidote import implementation, implements, register, world
from antidote.core import DependencyContainer
from antidote.core.exceptions import DependencyInstantiationError
from antidote.providers import FactoryProvider, IndirectProvider


@pytest.fixture(autouse=True)
def test_world():
    with world.test.empty():
        c = world.get(DependencyContainer)
        c.register_provider(FactoryProvider())
        c.register_provider(IndirectProvider())
        yield


class IService:
    pass


def test_implements():
    @implements(IService)
    @register
    class Service(IService):
        pass

    assert world.get(IService) is world.get(Service)


def test_default_implementation():
    @register
    class ServiceA(IService):
        pass

    @register
    class ServiceB(IService):
        pass

    choice = 'a'

    @implementation(IService)
    def choose():
        return dict(a=ServiceA, b=ServiceB)[choice]

    assert world.get(IService) is world.get(ServiceA)
    choice = 'b'
    assert choose() is ServiceB
    assert world.get(IService) is world.get(ServiceA)


@pytest.mark.parametrize('singleton,static',
                         [(True, True), (True, False), (False, True), (False, False)])
def test_implementation(singleton: bool, static: bool):
    choice = 'a'

    @register(singleton=singleton)
    class ServiceA(IService):
        pass

    @register(singleton=singleton)
    class ServiceB(IService):
        pass

    @implementation(IService, static=static)
    def choose_service():
        return dict(a=ServiceA, b=ServiceB)[choice]

    assert isinstance(world.get(IService), ServiceA)
    assert (world.get(IService) is world.get(ServiceA)) is singleton

    choice = 'b'
    assert choose_service() == ServiceB
    if static:
        assert isinstance(world.get(IService), ServiceA)
        assert (world.get(IService) is world.get(ServiceA)) is singleton
    else:
        assert isinstance(world.get(IService), ServiceB)
        assert (world.get(IService) is world.get(ServiceB)) is singleton


def test_invalid_implements():
    with pytest.raises(TypeError):
        @implements(IService)
        class A:
            pass

    with pytest.raises(TypeError):
        implements(IService)(1)

    with pytest.raises(TypeError):
        implements(1)


def test_invalid_implementation():
    with pytest.raises(TypeError):
        implementation(IService)(1)

    with pytest.raises(TypeError):
        @implementation(IService)
        class Service(IService):
            pass

    with pytest.raises(TypeError):
        implementation(1)

    class Service:
        pass

    world.singletons.set(Service, 1)
    world.singletons.set(1, 1)

    with world.test.clone():
        with pytest.raises(DependencyInstantiationError):
            @implementation(IService)
            def choose():
                return 1

            world.get(IService)

    with world.test.clone():
        with pytest.raises(DependencyInstantiationError):
            @implementation(IService)
            def choose():
                return Service

            world.get(IService)
