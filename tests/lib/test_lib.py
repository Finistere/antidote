import pytest

from antidote import (
    antidote_lib,
    antidote_lib_injectable,
    antidote_lib_interface,
    antidote_lib_lazy,
    DependencyNotFoundError,
    world,
)


def test_double_antidote_lazy() -> None:
    world.include(antidote_lib_lazy)
    # Should not fail
    world.include(antidote_lib_lazy)


def test_double_antidote_injectable() -> None:
    world.include(antidote_lib_injectable)
    # Should not fail
    world.include(antidote_lib_injectable)


def test_double_antidote_interface() -> None:
    world.include(antidote_lib_interface)
    # Should not fail
    world.include(antidote_lib_interface)


def test_double_antidote_lib() -> None:
    world.include(antidote_lib)
    # Should not fail
    world.include(antidote_lib)


def test_unknown_dependency() -> None:
    world.include(antidote_lib)

    class Dummy:
        pass

    # Ensures all providers work correctly with an unknown dependency
    with pytest.raises(DependencyNotFoundError):
        _ = world[Dummy]

    assert Dummy not in world
    assert "Unknown" in world.debug(Dummy)
