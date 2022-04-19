import pytest

from antidote import injectable, world
from antidote.core.exceptions import DependencyNotFoundError
from antidote.lib.injectable import register_injectable_provider


def test_clone() -> None:
    with world.test.empty():
        register_injectable_provider()

        @injectable
        class Dummy:
            pass

        class Service:
            pass

        original_dummy = world.get(Dummy)
        assert isinstance(original_dummy, Dummy)

        with world.test.clone(frozen=False):
            new_dummy = world.get(Dummy)
            assert isinstance(new_dummy, Dummy)
            assert new_dummy is not original_dummy

            injectable(Service)
            assert isinstance(world.get(Service), Service)

        assert world.get(Dummy) is original_dummy
        with pytest.raises(DependencyNotFoundError):
            world.get(Service)

        with world.test.clone(keep_singletons=True):
            assert world.get(Dummy) is original_dummy
