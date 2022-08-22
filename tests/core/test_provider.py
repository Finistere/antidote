# pyright: reportUnusedClass=false
from __future__ import annotations

from typing import ClassVar

import pytest

from antidote import FrozenCatalogError, world
from antidote.core import DependencyDebug, ProvidedDependency, Provider
from tests.core.dummy_providers import DummyProvider
from tests.utils import Obj

x = Obj()


def test_abstract_provider_base_implementations() -> None:
    @world.include
    class XProvider(Provider):
        def can_provide(self, dependency: object) -> bool:
            return super().can_provide(dependency)

        def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
            return super().unsafe_maybe_provide(dependency, out)

    provider = world.providers[XProvider]
    assert isinstance(provider, XProvider)

    with pytest.raises(NotImplementedError):
        provider.can_provide(object())

    with pytest.raises(NotImplementedError):
        provider.unsafe_maybe_provide(object(), object())  # type: ignore

    with world.test.clone():
        assert world.providers[XProvider] is not provider

    with world.test.copy():
        assert world.providers[XProvider] is not provider


def test_abstract_provider() -> None:
    @world.include
    class XProvider(Provider):
        known: ClassVar[set[object]] = set()

        def can_provide(self, dependency: object) -> bool:
            return dependency in self.known

        def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
            ...

    provider: XProvider = world.providers[XProvider]
    public = Obj()
    unknown = Obj()
    XProvider.known.add(public)

    assert provider.can_provide(public)
    assert not provider.can_provide(unknown)

    assert isinstance(provider.maybe_debug(public), DependencyDebug)
    assert provider.maybe_debug(unknown) is None


def test_missing_methods() -> None:
    with pytest.raises(TypeError):

        @world.include  # type: ignore
        class InvalidProvider(Provider):
            ...


def test_provider_catalog() -> None:
    world.include(DummyProvider)
    provider = world.providers[DummyProvider]
    provider.data[x] = x
    p_catalog = provider.catalog

    assert x in p_catalog
    assert p_catalog[x] is x
    assert p_catalog.get(x) is x
    assert p_catalog.get(object()) is None
    assert p_catalog.get(object(), x) is x

    assert not p_catalog.is_frozen
    p_catalog.raise_if_frozen()

    assert p_catalog.debug(x) == world.debug(x)

    world.freeze()

    assert p_catalog.is_frozen
    with pytest.raises(FrozenCatalogError):
        p_catalog.raise_if_frozen()

    assert str(world.private.id) in str(p_catalog)
    assert str(world.private.id) in repr(p_catalog)
