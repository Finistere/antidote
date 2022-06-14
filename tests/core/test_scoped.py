from __future__ import annotations

import itertools
from typing import TypeVar

import pytest

from antidote import inject, LifeTime, ScopeVar
from antidote.core import (
    DependencyDefinitionError,
    ProvidedDependency,
    PublicCatalog,
    ReadOnlyCatalog,
)
from tests.core.dummy_providers import DummyFactoryProvider
from tests.utils import Box, Obj

T = TypeVar("T")

x = Obj()


@pytest.fixture
def provider(catalog: PublicCatalog) -> DummyFactoryProvider:
    catalog.include(DummyFactoryProvider)
    return catalog.providers[DummyFactoryProvider]


def test_single_scope_var(catalog: PublicCatalog, provider: DummyFactoryProvider) -> None:
    a = ScopeVar(default="a", catalog=catalog)

    @provider.add_raw()
    def dummy(catalog: ReadOnlyCatalog, out: ProvidedDependency) -> None:
        out.set_value(
            value=Box(catalog[a]), lifetime=LifeTime.SCOPED, callback=lambda: Box(catalog[a])
        )

    result = catalog[dummy]
    assert result == Box("a")
    # cached
    assert result is catalog[dummy]

    a.set("a2")

    result2 = catalog[dummy]
    assert result2 == Box("a2")
    # cached
    assert result2 is catalog[dummy]


def test_multiple_scope_var(catalog: PublicCatalog, provider: DummyFactoryProvider) -> None:
    a = ScopeVar(default="a", catalog=catalog)
    b = ScopeVar(default="b", catalog=catalog)
    c = ScopeVar(default="c", catalog=catalog)

    @provider.add_raw()
    def dependency_ab(catalog: ReadOnlyCatalog, out: ProvidedDependency) -> None:
        out.set_value(
            value=Box((catalog[a], catalog[b])),
            lifetime=LifeTime.SCOPED,
            callback=lambda: Box((catalog[a], catalog[b])),
        )

    @provider.add_raw()
    def dependency_ac(catalog: ReadOnlyCatalog, out: ProvidedDependency) -> None:
        out.set_value(
            value=Box((catalog[a], catalog[c])),
            lifetime=LifeTime.SCOPED,
            callback=lambda: Box((catalog[a], catalog[c])),
        )

    ab = catalog[dependency_ab]
    ac = catalog[dependency_ac]
    assert ab == Box(("a", "b"))
    assert ac == Box(("a", "c"))
    assert catalog[dependency_ab] is ab
    assert catalog[dependency_ac] is ac

    c.set("c2")
    assert catalog[dependency_ab] is ab
    assert catalog[dependency_ac] is not ac
    ac = catalog[dependency_ac]
    assert ac == Box(("a", "c2"))

    a.set("a2")
    assert catalog[dependency_ab] is not ab
    assert catalog[dependency_ac] is not ac
    assert catalog[dependency_ab] == Box(("a2", "b"))
    assert catalog[dependency_ac] == Box(("a2", "c2"))


def test_singleton_cannot_depend_on_scoped(
    catalog: PublicCatalog, provider: DummyFactoryProvider
) -> None:
    a = ScopeVar(default="a", catalog=catalog)

    @provider.add_raw()
    def dummy(catalog: ReadOnlyCatalog, out: ProvidedDependency) -> None:
        out.set_value(
            value=Box(catalog[a]), lifetime=LifeTime.SCOPED, callback=lambda: Box(catalog[a])
        )

    class Injected:
        @inject(catalog=catalog)
        def __init__(self, d: object = inject[dummy]) -> None:
            ...

    class InitRetrieval:
        def __init__(self) -> None:
            self.d = catalog[dummy]

    provider.add(Injected, factory=lambda c: Injected())
    provider.add(InitRetrieval, factory=lambda c: InitRetrieval())

    assert Injected in catalog
    with pytest.raises(DependencyDefinitionError, match="(?i)singleton.*depend.*scoped"):
        _ = catalog[Injected]

    assert InitRetrieval in catalog
    with pytest.raises(DependencyDefinitionError, match="(?i)singleton.*depend.*scoped"):
        _ = catalog[InitRetrieval]

    @provider.add_raw()
    def indirect(catalog: ReadOnlyCatalog, out: ProvidedDependency) -> None:
        out.set_value(
            value=Box(catalog[dummy]),
            lifetime=LifeTime.TRANSIENT,
            callback=lambda: Box(catalog[dummy]),
        )

    class IndirectInjected:
        @inject(catalog=catalog)
        def __init__(self, d: object = inject[indirect]) -> None:
            ...

    class IndirectInitRetrieval:
        def __init__(self) -> None:
            self.d = catalog[indirect]

    provider.add(IndirectInjected, factory=lambda c: IndirectInjected())
    provider.add(IndirectInitRetrieval, factory=lambda c: IndirectInitRetrieval())

    assert IndirectInjected in catalog
    with pytest.raises(DependencyDefinitionError, match="(?i)singleton.*depend.*scoped"):
        _ = catalog[IndirectInjected]

    assert IndirectInitRetrieval in catalog
    with pytest.raises(DependencyDefinitionError, match="(?i)singleton.*depend.*scoped"):
        _ = catalog[IndirectInitRetrieval]


def test_can_change_state_tokens(catalog: PublicCatalog, provider: DummyFactoryProvider) -> None:
    a = ScopeVar(default="a", catalog=catalog)
    b = ScopeVar(default="b", catalog=catalog)

    @provider.add_raw()
    def dummy(catalog: ReadOnlyCatalog, out: ProvidedDependency) -> None:
        counter = itertools.count()

        def callback() -> object:
            if next(counter) % 2 == 0:
                return Box(catalog[a])
            return Box(catalog[b])

        out.set_value(value=callback(), lifetime=LifeTime.SCOPED, callback=callback)

    d1 = catalog[dummy]
    assert d1 == Box("a")
    assert catalog[dummy] is d1

    # change actual dependency
    a.set("a2")
    d2 = catalog[dummy]
    assert d2 == Box("b")
    assert catalog[dummy] is d2

    a.set("a3")  # has no impact anymore
    assert catalog[dummy] is d2

    b.set("b4")
    d3 = catalog[dummy]
    assert d3 == Box("a3")
    assert catalog[dummy] is d3

    a.set("a5")
    d4 = catalog[dummy]
    assert d4 == Box("b4")
    assert catalog[dummy] is d4


def test_scoped_must_depend_on_scope_vars(
    catalog: PublicCatalog, provider: DummyFactoryProvider
) -> None:
    @provider.add_raw()
    def dummy(catalog: ReadOnlyCatalog, out: ProvidedDependency) -> None:
        out.set_value(value=object(), lifetime=LifeTime.SCOPED, callback=object)

    with pytest.raises(DependencyDefinitionError, match="(?i)no scope vars"):
        _ = catalog[dummy]


def test_test_env(catalog: PublicCatalog, provider: DummyFactoryProvider) -> None:
    var = ScopeVar(default="default", catalog=catalog)

    @provider.add_raw()
    def dummy(catalog: ReadOnlyCatalog, out: ProvidedDependency) -> None:
        out.set_value(
            value=Box(catalog[var]), lifetime=LifeTime.SCOPED, callback=lambda: Box(catalog[var])
        )

    var.set("original")
    original = catalog[dummy]

    with catalog.test.clone():
        # Using default value
        assert catalog[dummy] == Box("default")
        assert catalog[dummy] is catalog[dummy]

        var.set("new")
        assert catalog[dummy] == Box("new")

    assert catalog[dummy] is original

    with catalog.test.copy():
        assert catalog[dummy] is original

        var.set("new")
        assert catalog[dummy] == Box("new")
        assert catalog[dummy] is catalog[dummy]

    assert catalog[dummy] is original
