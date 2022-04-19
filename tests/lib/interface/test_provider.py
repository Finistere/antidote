import pytest

from antidote import implements, interface, world
from antidote.core.exceptions import DependencyNotFoundError
from antidote.lib.injectable import register_injectable_provider
from antidote.lib.interface import register_interface_provider


def test_clone() -> None:
    with world.test.empty():
        register_interface_provider()
        register_injectable_provider()

        @interface
        class Base:
            pass

        @implements(Base)
        class A(Base):
            pass

        original_a = world.get(A)
        assert world.get[Base].single() is world.get(A)

        with world.test.clone(frozen=False):
            new_a = world.get(A)
            assert world.get[Base].single() is new_a
            assert new_a is not original_a

            @implements(Base)
            class B(Base):
                pass

            assert set(world.get[Base].all()) == {world.get(A), world.get(B)}

        with world.test.clone(keep_singletons=True):
            assert world.get[Base].single() is original_a

        assert world.get[Base].single() is original_a


def test_unknown_interface() -> None:
    class Dummy:
        pass

    with world.test.empty():
        register_interface_provider()
        with pytest.raises(DependencyNotFoundError):
            world.get[object](Dummy)
