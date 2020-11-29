import pytest

from antidote import factory, implementation, Implementation, Service, world
from antidote._extension.providers import (FactoryProvider, IndirectProvider,
                                           ServiceProvider)
from antidote.exceptions import DependencyInstantiationError


@pytest.fixture(autouse=True)
def test_world():
    with world.test.empty():
        world.provider(ServiceProvider)
        world.provider(FactoryProvider)
        world.provider(IndirectProvider)
        yield


class Interface:
    pass


def test_implementation_class():
    class A(Interface, Implementation):
        pass

    assert world.get(Interface) is world.get(A)


def test_default_implementation():
    class A(Interface, Service):
        pass

    class B(Interface, Service):
        pass

    choice = 'a'

    @implementation(Interface)
    def choose():
        return dict(a=A, b=B)[choice]

    assert world.get(Interface) is world.get(A)
    choice = 'b'
    assert choose() is B
    assert world.get(Interface) is world.get(A)


@pytest.mark.parametrize('singleton,permanent',
                         [(True, True), (True, False), (False, True), (False, False)])
def test_implementation(singleton: bool, permanent: bool):
    choice = 'a'

    class A(Interface, Service):
        __antidote__ = Service.Conf(singleton=singleton)

    class B(Interface, Service):
        __antidote__ = Service.Conf(singleton=singleton)

    @implementation(Interface, permanent=permanent)
    def choose_service():
        return dict(a=A, b=B)[choice]

    assert isinstance(world.get(Interface), A)
    assert (world.get(Interface) is world.get(A)) is singleton

    choice = 'b'
    assert choose_service() == B
    if permanent:
        assert isinstance(world.get(Interface), A)
        assert (world.get(Interface) is world.get(A)) is singleton
    else:
        assert isinstance(world.get(Interface), B)
        assert (world.get(Interface) is world.get(B)) is singleton


def test_implementation_integration():
    x = object()

    with world.test.clone():
        class A(Interface, Service):
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        @implementation(Interface)
        def impl():
            return A.with_kwargs(test=x)

        a = world.get(Interface)
        assert isinstance(a, A)
        assert a.kwargs == dict(test=x)

    with world.test.clone():
        class A(Interface):
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        @factory
        def build_a(**kwargs) -> A:
            return A(**kwargs)

        @implementation(Interface)
        def impl2():
            return A @ build_a.with_kwargs(test=x)

        a = world.get(Interface)
        assert isinstance(a, A)
        assert a.kwargs == dict(test=x)


def test_invalid_implementation_class():
    with pytest.raises(TypeError):
        class A(Implementation):
            pass

    with pytest.raises(TypeError):
        class B(Implementation, Interface):
            pass

    with pytest.raises(TypeError):
        class C(Interface, Implementation, Implementation):
            pass

    with pytest.raises(ValueError):
        class D(Interface, Implementation, abstract=True):
            pass


def test_invalid_implementation():
    with pytest.raises(TypeError):
        implementation(Interface)(1)

    with pytest.raises(TypeError):
        @implementation(Interface)
        class A(Interface):
            pass

    with pytest.raises(TypeError):
        implementation(1)

    class B:
        pass

    world.singletons.add(B, 1)
    world.singletons.add(1, 1)

    with world.test.clone(keep_singletons=True):
        @implementation(Interface)
        def choose():
            return 1

        world.get(1)
        with pytest.raises(DependencyInstantiationError):
            world.get(Interface)

    with world.test.clone(keep_singletons=True):
        @implementation(Interface)
        def choose2():
            return B

        world.get(B)
        with pytest.raises(DependencyInstantiationError):
            world.get(Interface)

    with world.test.clone():
        class C(Service):
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        @implementation(Interface)
        def impl():
            return C.with_kwargs(test=1)

        world.get(C.with_kwargs(test=1))
        with pytest.raises(DependencyInstantiationError):
            world.get(Interface)

    with world.test.clone():
        class D:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        @factory
        def build_d(**kwargs) -> D:
            return D(**kwargs)

        @implementation(Interface)
        def impl2():
            return D @ build_d.with_kwargs(test=1)

        world.get(D @ build_d.with_kwargs(test=1))
        with pytest.raises(DependencyInstantiationError):
            world.get(Interface)
