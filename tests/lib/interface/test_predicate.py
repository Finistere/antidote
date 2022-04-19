from typing import Iterator

import pytest

from antidote import world
from antidote.lib.injectable import register_injectable_provider
from antidote.lib.interface import NeutralWeight, register_interface_provider


@pytest.fixture(autouse=True)
def setup_world() -> Iterator[None]:
    with world.test.empty():
        register_injectable_provider()
        register_interface_provider()
        yield


def test_neutral_weight() -> None:
    neutral = NeutralWeight()
    assert NeutralWeight() is neutral
    assert (NeutralWeight() + NeutralWeight()) == neutral
    assert not (NeutralWeight() < neutral)
