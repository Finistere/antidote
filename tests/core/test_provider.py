# pyright: reportUnusedClass=false
from __future__ import annotations

from typing import ClassVar

import pytest

from antidote import world
from antidote.core import DependencyDebug, ProvidedDependency, Provider
from tests.utils import Obj


def test_abstract_provider_base_implementations() -> None:
    @world.include
    class DummyProvider(Provider):
        def can_provide(self, dependency: object) -> bool:
            return super().can_provide(dependency)

        def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
            return super().unsafe_maybe_provide(dependency, out)

    provider = world.providers[DummyProvider]
    assert isinstance(provider, DummyProvider)

    with pytest.raises(NotImplementedError):
        provider.can_provide(object())

    with pytest.raises(NotImplementedError):
        provider.unsafe_maybe_provide(object(), object())  # type: ignore

    with world.test.clone():
        assert world.providers[DummyProvider] is not provider

    with world.test.copy():
        assert world.providers[DummyProvider] is not provider


def test_abstract_provider() -> None:
    @world.include
    class DummyProvider(Provider):
        known: ClassVar[set[object]] = set()

        def can_provide(self, dependency: object) -> bool:
            return dependency in self.known

        def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
            ...

    provider = world.providers[DummyProvider]
    public = Obj()
    unknown = Obj()
    DummyProvider.known.add(public)

    assert provider.can_provide(public)
    assert not provider.can_provide(unknown)

    assert isinstance(provider.maybe_debug(public), DependencyDebug)
    assert provider.maybe_debug(unknown) is None


def test_missing_methods() -> None:
    with pytest.raises(TypeError):

        @world.include  # type: ignore
        class InvalidProvider(Provider):
            ...
