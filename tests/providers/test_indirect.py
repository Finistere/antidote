from typing import Callable

import pytest

from antidote import world
from antidote.exceptions import DuplicateDependencyError, FrozenWorldError
from antidote.providers import IndirectProvider, ServiceProvider


class Interface:
    pass


class A(Interface):
    pass


class B(Interface):
    pass


@pytest.fixture(autouse=True)
def empty_world():
    with world.test.empty():
        yield


@pytest.fixture
def service():
    world.provider(ServiceProvider)
    return world.get(ServiceProvider)


@pytest.fixture
def indirect():
    world.provider(IndirectProvider)
    return world.get(IndirectProvider)


def test_none(indirect: IndirectProvider):
    assert indirect.test_provide(Interface) is None


def test_simple(indirect: IndirectProvider):
    world.singletons.set(A, A())
    indirect.register_static(Interface, A)

    assert indirect.test_provide(Interface).instance is world.get(A)
    assert indirect.test_provide(Interface).singleton is True
    assert str(Interface) in repr(indirect)


def test_not_singleton_interface(indirect: IndirectProvider,
                                 service: ServiceProvider):
    service.register(A, singleton=False)
    indirect.register_static(Interface, A)

    assert indirect.test_provide(Interface).instance is not world.get(A)
    assert isinstance(indirect.test_provide(Interface).instance, A)
    assert indirect.test_provide(Interface).singleton is False


@pytest.mark.parametrize('singleton', [True, False])
@pytest.mark.parametrize('permanent', [True, False])
def test_link_permanent_singleton(indirect: IndirectProvider,
                                  service: ServiceProvider,
                                  singleton: bool,
                                  permanent: bool):
    choice = 'a'

    def implementation():
        return dict(a=A, b=B)[choice]

    service.register(A, singleton=singleton)
    service.register(B, singleton=singleton)
    indirect.register_link(Interface, linker=implementation, permanent=permanent)

    instance = indirect.test_provide(Interface).instance
    assert isinstance(instance, A)
    assert (instance is world.get(A)) is singleton
    assert indirect.test_provide(Interface).singleton is (singleton and permanent)

    choice = 'b'
    assert implementation() == B
    assert indirect.test_provide(Interface).singleton is (singleton and permanent)
    instance = indirect.test_provide(Interface).instance
    if permanent:
        assert isinstance(instance, A)
        assert (instance is world.get(A)) is singleton
    else:
        assert isinstance(instance, B)
        assert (instance is world.get(B)) is singleton


@pytest.mark.parametrize('keep_singletons_cache', [True, False])
@pytest.mark.parametrize('register', [
    pytest.param(lambda indirect, inf, impl: indirect.register_static(inf, impl),
                 id='register_static'),
    pytest.param(
        lambda indirect, inf, impl: indirect.register_link(inf, lambda: impl,
                                                           permanent=False),
        id='register_link'),
    pytest.param(
        lambda indirect, inf, impl: indirect.register_link(inf, lambda: impl,
                                                           permanent=True),
        id='register_link_permanent')
])
def test_copy(indirect: IndirectProvider,
              keep_singletons_cache: bool,
              register: Callable[[IndirectProvider, type, type], object]):
    world.singletons.update({A: A()})

    register(indirect, Interface, A)
    a = indirect.test_provide(Interface).instance
    assert isinstance(a, Interface)

    if keep_singletons_cache:
        with world.test.clone(keep_singletons=True):
            clone = indirect.clone(keep_singletons_cache=True)
            assert clone.test_provide(Interface).instance is a
    else:
        with world.test.empty():
            world.singletons.update({A: A(), B: B()})
            clone = indirect.clone(keep_singletons_cache=False)
            instance = clone.test_provide(Interface).instance
            assert instance is world.get(A)
            assert instance is not a

    class Interface2:
        pass

    class A2(Interface2):
        pass

    class Interface3:
        pass

    class A3(Interface3):
        pass

    world.singletons.update({A2: A2(), A3: A3()})
    # Original does not modify clone
    register(indirect, Interface2, A2)
    assert indirect.test_provide(Interface2).instance is world.get(A2)
    assert clone.test_provide(Interface2) is None

    # Did not modify original provider
    register(clone, Interface3, A3)
    assert clone.test_provide(Interface3).instance is world.get(A3)
    assert indirect.test_provide(Interface3) is None


def test_freeze(indirect: IndirectProvider):
    world.freeze()

    with pytest.raises(FrozenWorldError):
        indirect.register_link(Interface, lambda: A, permanent=False)

    with pytest.raises(FrozenWorldError):
        indirect.register_static(Interface, A)

    assert indirect.test_provide(Interface) is None


def test_register_static_duplicate_check(indirect: IndirectProvider):
    indirect.register_static(Interface, A)

    with pytest.raises(DuplicateDependencyError):
        indirect.register_static(Interface, A)

    with pytest.raises(DuplicateDependencyError):
        indirect.register_link(Interface, lambda: A)


def test_register_duplicate_check(indirect: IndirectProvider):
    indirect.register_link(Interface, lambda: A)

    with pytest.raises(DuplicateDependencyError):
        indirect.register_static(Interface, A)

    with pytest.raises(DuplicateDependencyError):
        indirect.register_link(Interface, lambda: A)
