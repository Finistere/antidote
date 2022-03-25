from typing import Iterator

import pytest

from antidote import world
from antidote._providers import ServiceProvider
from antidote.lib.interface import NeutralWeight, register_interface_provider


@pytest.fixture(autouse=True)
def setup_world() -> Iterator[None]:
    with world.test.empty():
        world.provider(ServiceProvider)
        register_interface_provider()
        yield


def test_neutral_weight() -> None:
    neutral = NeutralWeight()
    assert NeutralWeight() is neutral
    assert (NeutralWeight() + NeutralWeight()) == neutral
    assert not (NeutralWeight() < neutral)
