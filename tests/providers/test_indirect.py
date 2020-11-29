from typing import Callable

import pytest

from antidote import world
from antidote.core.exceptions import DependencyNotFoundError
from antidote.exceptions import DuplicateDependencyError, FrozenWorldError
from antidote._extension.providers import IndirectProvider, ServiceProvider


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
def service(empty_world):
    world.provider(ServiceProvider)
    return world.get(ServiceProvider)


@pytest.fixture
def indirect(empty_world):
    world.provider(IndirectProvider)
    return world.get(IndirectProvider)


def test_simple():
    indirect = IndirectProvider()
    world.singletons.add(A, A())
    indirect.register_static(Interface, A)

    assert world.test.maybe_provide_from(indirect, Interface).value is world.get(A)
    assert world.test.maybe_provide_from(indirect, Interface).singleton is True
    assert str(Interface) in repr(indirect)


def test_static_exists():
    indirect = IndirectProvider()
    world.singletons.add(A, A())
    indirect.register_static(Interface, A)

    assert not indirect.exists(object())
    assert indirect.exists(Interface)
    assert not indirect.exists(A)


def test_link_exists():
    indirect = IndirectProvider()
    world.singletons.add(A, A())
    indirect.register_link(Interface, lambda: A)

    assert not indirect.exists(object())
    assert indirect.exists(Interface)
    assert not indirect.exists(A)


def test_not_singleton_interface(service: ServiceProvider):
    indirect = IndirectProvider()
    service.register(A, singleton=False)
    indirect.register_static(Interface, A)

    assert world.test.maybe_provide_from(indirect, Interface).value is not world.get(A)
    assert isinstance(world.test.maybe_provide_from(indirect, Interface).value, A)
    assert world.test.maybe_provide_from(indirect, Interface).singleton is False


@pytest.mark.parametrize('singleton', [True, False])
@pytest.mark.parametrize('permanent', [True, False])
def test_link_permanent_singleton(service: ServiceProvider,
                                  singleton: bool,
                                  permanent: bool):
    choice = 'a'

    def implementation():
        return dict(a=A, b=B)[choice]

    service.register(A, singleton=singleton)
    service.register(B, singleton=singleton)
    indirect = IndirectProvider()
    indirect.register_link(Interface, linker=implementation, permanent=permanent)

    instance = world.test.maybe_provide_from(indirect, Interface).value
    assert isinstance(instance, A)
    assert (instance is world.get(A)) is singleton
    assert world.test.maybe_provide_from(indirect,
                                         Interface).singleton is (singleton and permanent)

    choice = 'b'
    assert implementation() == B
    assert world.test.maybe_provide_from(indirect,
                                         Interface).singleton is (singleton and permanent)
    instance = world.test.maybe_provide_from(indirect, Interface).value
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
    world.singletons.add_all({A: A()})

    register(indirect, Interface, A)
    a = world.get(Interface)
    assert isinstance(a, Interface)

    if keep_singletons_cache:
        with world.test.clone(keep_singletons=True):
            clone = indirect.clone(True)
            assert world.test.maybe_provide_from(clone, Interface).value is a
    else:
        with world.test.empty():
            world.singletons.add_all({A: A(), B: B()})
            clone = indirect.clone(False)
            instance = world.test.maybe_provide_from(clone, Interface).value
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

    world.singletons.add_all({A2: A2(), A3: A3()})
    # Original does not modify clone
    register(indirect, Interface2, A2)
    assert world.get(Interface2) is world.get(A2)
    assert world.test.maybe_provide_from(clone, Interface2) is None

    # Did not modify original provider
    register(clone, Interface3, A3)
    assert world.test.maybe_provide_from(clone, Interface3).value is world.get(A3)
    with pytest.raises(DependencyNotFoundError):
        world.get(Interface3)


def test_freeze(indirect: IndirectProvider):
    world.freeze()

    with pytest.raises(FrozenWorldError):
        indirect.register_link(Interface, lambda: A, permanent=False)

    with pytest.raises(FrozenWorldError):
        indirect.register_static(Interface, A)

    with pytest.raises(DependencyNotFoundError):
        world.get(Interface)


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


def test_invalid_link():
    indirect = IndirectProvider()
    indirect.register_static('A', 'B')

    with pytest.raises(DependencyNotFoundError, match=".*B.*"):
        world.test.maybe_provide_from(indirect, 'A')

    for permanent in [True, False]:
        origin = f'origin-{permanent}'
        target = f'target-{permanent}'

        def impl():
            return target

        indirect.register_link(origin, linker=impl, permanent=permanent)

        with pytest.raises(DependencyNotFoundError, match=".*" + target + ".*"):
            world.test.maybe_provide_from(indirect, origin)
