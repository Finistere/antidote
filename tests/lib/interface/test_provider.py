import pytest

from antidote import implements, interface, world
from antidote._providers import ServiceProvider
from antidote.core.exceptions import DependencyNotFoundError
from antidote.lib.interface import register_interface_provider
from antidote.lib.interface._provider import Query


def test_clone() -> None:
    with world.test.empty():
        register_interface_provider()
        world.provider(ServiceProvider)

        @interface
        class Base:
            pass

        @implements(Base)
        class A(Base):
            pass

        assert world.get[Base].single() is world.get(A)

        with world.test.clone(frozen=False):
            @implements(Base)
            class B(Base):
                pass

            assert set(world.get[Base].all()) == {world.get(A), world.get(B)}

        assert world.get[Base].single() is world.get(A)


def test_unknown_interface() -> None:
    class Dummy:
        pass

    with world.test.empty():
        register_interface_provider()
        with pytest.raises(DependencyNotFoundError):
            world.get[object](Query(interface=Dummy, constraints=[], all=False))
