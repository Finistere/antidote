from __future__ import annotations

import pytest

from antidote import inject, injectable, world
from antidote.core.exceptions import DependencyNotFoundError
from antidote.lib.injectable import antidote_injectable
from tests.utils import expected_debug


def test_clone() -> None:
    world.include(antidote_injectable)

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
        world[Service]

    with world.test.copy():
        assert world.get(Dummy) is original_dummy


def test_debug() -> None:
    world.include(antidote_injectable)

    @injectable
    class Dummy:
        pass

    @injectable
    class SuperDummy:
        def __init__(self, dummy: Dummy = inject.me()) -> None:
            ...

    @injectable(factory_method="create")
    class FactoryDummy:
        @classmethod
        def create(cls, dummy: Dummy = inject.me()) -> FactoryDummy:
            ...

    namespace = "tests.lib.injectable.test_provider.test_debug.<locals>"

    assert "Unknown" in world.debug(object())  # should not fail
    assert world.debug(Dummy) == expected_debug(
        f"""
        🟉 {namespace}.Dummy
        """
    )
    assert world.debug(SuperDummy) == expected_debug(
        f"""
        🟉 {namespace}.SuperDummy
        └── {namespace}.SuperDummy.__init__
            └── 🟉 {namespace}.Dummy
        """
    )
    assert world.debug(FactoryDummy) == expected_debug(
        f"""
        🟉 {namespace}.FactoryDummy
        └── {namespace}.FactoryDummy.create
            └── 🟉 {namespace}.Dummy
        """
    )
