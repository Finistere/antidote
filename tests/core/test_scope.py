# pyright: reportUnusedFunction=false
from __future__ import annotations

import pytest

from antidote import (
    DependencyNotFoundError,
    FrozenCatalogError,
    new_catalog,
    PublicCatalog,
    ScopeGlobalVar,
    UndefinedScopeVarError,
    world,
)
from antidote.core import DependencyDefinitionError
from tests.core.dummy_providers import DummyFactoryProvider
from tests.utils import Box, expected_debug, Obj

x = Obj()
y = Obj()


def test_scope_var(catalog: PublicCatalog) -> None:
    dummy = ScopeGlobalVar(default="Hello", catalog=catalog)
    assert catalog[dummy] == "Hello"

    token = dummy.set("catalog")
    assert token.var is dummy
    assert token.old_value == "Hello"
    assert catalog[dummy] == "catalog"

    dummy.reset(token)
    assert catalog[dummy] == "Hello"


def test_name_repr(catalog: PublicCatalog) -> None:
    dummy = ScopeGlobalVar[object](catalog=catalog)
    assert "dummy" in dummy.name
    assert "tests.core.test_scope" in dummy.name
    assert "dummy" in repr(dummy)
    assert "tests.core.test_scope" in repr(dummy)
    assert str(catalog.id) in repr(dummy)
    assert "dummy" in catalog.debug(dummy)
    assert "tests.core.test_scope" in repr(dummy)

    named = ScopeGlobalVar[object](name="John", catalog=catalog)
    assert "John" == named.name
    assert "John" in repr(named)
    assert "John" in catalog.debug(named)

    class Namespace:
        dummy = ScopeGlobalVar[object](catalog=catalog)
        named = ScopeGlobalVar[object](name="Wick", catalog=catalog)

    expected_name = "tests.core.test_scope.test_name_repr.<locals>.Namespace.dummy"
    assert Namespace.dummy.name == expected_name
    assert expected_name in repr(Namespace.dummy)
    assert str(catalog.id) in repr(Namespace.dummy)
    assert expected_name in catalog.debug(Namespace.dummy)

    assert "Wick" == Namespace.named.name
    assert "Wick" in repr(Namespace.named)
    assert "Wick" in catalog.debug(Namespace.named)

    with pytest.raises(ValueError, match="name"):
        ScopeGlobalVar(name="?!@#")


def test_no_default(catalog: PublicCatalog) -> None:
    dummy = ScopeGlobalVar[object](catalog=catalog)

    with pytest.raises(UndefinedScopeVarError, match="dummy"):
        _ = catalog[dummy]

    token = dummy.set("value")
    assert catalog[dummy] == "value"

    dummy.reset(token)
    with pytest.raises(UndefinedScopeVarError, match="dummy"):
        _ = catalog[dummy]


def test_catalog() -> None:
    catalog = new_catalog(include=[])
    dummy = ScopeGlobalVar[object](catalog=catalog)
    world_dummy = ScopeGlobalVar[object]()

    assert dummy in catalog
    assert dummy not in world
    assert world_dummy not in catalog
    assert world_dummy in world

    with pytest.raises(TypeError, match="catalog"):
        ScopeGlobalVar[object](catalog=object())  # type: ignore


def test_debug(catalog: PublicCatalog) -> None:
    class Namespace:
        dummy = ScopeGlobalVar[object](catalog=catalog)

    assert catalog.debug(Namespace.dummy) == expected_debug(
        """
    <scope-global-var> tests.core.test_scope.test_debug.<locals>.Namespace.dummy
    """
    )


def test_frozen(catalog: PublicCatalog) -> None:
    catalog.freeze()
    with pytest.raises(FrozenCatalogError):
        ScopeGlobalVar[object](catalog=catalog)


def test_test_env(catalog: PublicCatalog) -> None:
    dummy = ScopeGlobalVar[Box[str]](catalog=catalog)
    dummy2 = ScopeGlobalVar[object](default=x, catalog=catalog)

    original = Box("Hello")
    dummy.set(original)
    dummy2.set(y)

    with catalog.test.empty():
        assert dummy not in catalog
        assert dummy2 not in catalog

        with pytest.raises(DependencyNotFoundError, match="dummy"):
            dummy.set(Box("x"))

    assert catalog[dummy] is original
    assert catalog[dummy2] is y

    with catalog.test.new():
        assert dummy not in catalog
        assert dummy2 not in catalog

    assert catalog[dummy] is original
    assert catalog[dummy2] is y

    with catalog.test.clone():
        assert dummy in catalog
        assert dummy2 in catalog

        with pytest.raises(UndefinedScopeVarError, match="dummy"):
            _ = catalog[dummy]

        assert catalog[dummy2] is x

        dummy.set(Box("catalog"))
        dummy2.set(object())

    assert catalog[dummy] is original
    assert catalog[dummy2] is y

    with catalog.test.copy():
        assert dummy in catalog
        assert dummy2 in catalog
        assert catalog[dummy] is original
        assert catalog[dummy2] is y
        dummy.set(Box("catalog"))
        dummy2.set(object())

    assert catalog[dummy] is original
    assert catalog[dummy2] is y


def test_singleton_cannot_depend_on_state_var(catalog: PublicCatalog) -> None:
    catalog.include(DummyFactoryProvider)
    provider = catalog.providers[DummyFactoryProvider]
    dummy = ScopeGlobalVar(default="Hello", catalog=catalog)

    provider.add(x, factory=lambda c: c[dummy], lifetime="singleton")

    with pytest.raises(DependencyDefinitionError, match="(?i)singleton.*scope var"):
        _ = catalog[x]
