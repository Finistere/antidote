# pyright: reportUnusedClass=false
from __future__ import annotations

import re
from abc import ABC
from typing import Callable

import pytest

from antidote.core import (
    Catalog,
    CatalogId,
    DependencyDebug,
    DependencyDefinitionError,
    DependencyNotFoundError,
    FrozenCatalogError,
    LifeTime,
    MissingProviderError,
    new_catalog,
    ProvidedDependency,
    Provider,
    PublicCatalog,
    ReadOnlyCatalog,
)
from antidote.core.exceptions import DuplicateProviderError
from tests.core.dummy_providers import DummyFactoryProvider, DummyProvider

x = object()
y = object()
z = object()


class A:
    ...


class B:
    ...


class C:
    ...


@pytest.fixture
def dummy_provider(catalog: Catalog) -> DummyProvider:
    catalog.include(DummyProvider)
    return catalog.providers[DummyProvider]


@pytest.fixture
def dummy_factory_provider(catalog: Catalog) -> DummyFactoryProvider:
    catalog.include(DummyFactoryProvider)
    return catalog.providers[DummyFactoryProvider]


def test_empty(catalog: PublicCatalog) -> None:
    # Should not fail
    with catalog.test.new():
        pass

    with catalog.test.clone():
        pass

    with catalog.test.empty():
        pass

    assert x not in catalog

    with pytest.raises(DependencyNotFoundError, match=str(x)):
        _ = catalog[x]

    assert catalog.get(x) is None
    assert catalog.debug(x) == f"/!\\ Unknown: {x!r}"
    assert catalog.get(x, default=y) is y

    assert not catalog.is_frozen

    # should not raise any error
    catalog.raise_if_frozen()


def test_provider(catalog: PublicCatalog) -> None:
    catalog.include(DummyProvider)
    # also included in private by default
    for c in [catalog, catalog.private]:
        assert isinstance(c.providers[DummyProvider], DummyProvider)
        assert DummyProvider in c.providers
        assert c.providers[DummyProvider] is c.providers[DummyProvider]

    with pytest.raises(DuplicateProviderError, match="DummyProvider"):
        catalog.include(DummyProvider)

    # but including in private, does not include in public
    catalog.private.include(DummyFactoryProvider)
    assert DummyFactoryProvider in catalog.private.providers
    assert DummyFactoryProvider not in catalog.providers
    private_factory_provider = catalog.private.providers[DummyFactoryProvider]

    catalog.include(DummyFactoryProvider)
    assert DummyFactoryProvider in catalog.providers
    assert catalog.private.providers[DummyFactoryProvider] is private_factory_provider
    assert DummyFactoryProvider.__name__ in repr(catalog.providers)

    with pytest.raises(TypeError, match="Provider subclass"):
        catalog.include(object())  # type: ignore

    with pytest.raises(MissingProviderError):
        catalog.providers[object()]  # type: ignore

    with pytest.raises(KeyError):
        catalog.providers[object()]  # type: ignore


def test_simple_value(catalog: PublicCatalog, dummy_provider: DummyProvider) -> None:
    dummy_provider.data = {"name": "Antidote"}
    assert "name" in catalog
    assert catalog["name"] == "Antidote"
    assert catalog.get("name") == "Antidote"


def test_singleton(catalog: PublicCatalog, dummy_factory_provider: DummyFactoryProvider) -> None:
    (
        dummy_factory_provider.add(dependency=A, lifetime="singleton", factory=lambda _: A()).add(
            dependency=B, lifetime="transient", factory=lambda _: B()
        )
    )

    # Singleton
    a = catalog[A]
    assert A in catalog
    assert catalog[A] is a
    assert catalog.get(A) is a

    # B is not a singleton
    b = catalog[B]
    assert B in catalog
    assert catalog[B] is not b
    assert catalog.get(B) is not b


def test_dependency_cannot_be_provided_error(
    catalog: PublicCatalog, dummy_factory_provider: DummyFactoryProvider
) -> None:
    def raise_error() -> None:
        raise RuntimeError("Hello!")

    (
        dummy_factory_provider.add(A, factory=lambda c: c[B], lifetime="transient")
        .add(B, factory=lambda c: c[C], lifetime="transient")
        .add(C, factory=lambda _: raise_error(), lifetime="transient")
    )

    with pytest.raises(RuntimeError, match="Hello!"):
        catalog.get(C)

    with pytest.raises(RuntimeError, match="Hello!"):
        catalog.get(A)


def test_freeze(catalog: PublicCatalog) -> None:
    private_catalog = catalog.private
    # registration possible, locking possible
    private_catalog.include(DummyFactoryProvider)
    catalog.include(DummyFactoryProvider)
    catalogs = [catalog, private_catalog]

    with pytest.raises(AttributeError, match="freeze"):
        private_catalog.freeze()  # type: ignore

    for c in catalogs:
        assert not c.is_frozen
        c.raise_if_frozen()

    # will also freeze private catalog
    catalog.freeze()
    for c in catalogs:
        assert c.is_frozen

    with pytest.raises(FrozenCatalogError):
        catalog.include(DummyProvider)

    with pytest.raises(FrozenCatalogError):
        catalog.include(new_catalog(include=[]))

    with pytest.raises(FrozenCatalogError):
        private_catalog.include(DummyProvider)

    with pytest.raises(FrozenCatalogError):
        catalog.raise_if_frozen()

    with pytest.raises(FrozenCatalogError):
        private_catalog.raise_if_frozen()

    with pytest.raises(FrozenCatalogError):
        catalog.freeze()


def test_freeze_child_before_parent(catalog: PublicCatalog, nested_catalog: PublicCatalog) -> None:
    nested_catalog.freeze()
    assert nested_catalog.is_frozen
    assert not catalog.is_frozen

    # does not raise an exception with nested already frozen
    catalog.freeze()
    assert catalog.is_frozen


def test_freeze_parent_before_child(catalog: PublicCatalog, nested_catalog: PublicCatalog) -> None:
    catalog.freeze()
    assert catalog.is_frozen
    assert nested_catalog.is_frozen


def test_debug(catalog: PublicCatalog, dummy_provider: DummyProvider) -> None:
    dummy_provider.data = {x: x}
    assert "No debug provided" in catalog.debug(x)
    assert DummyProvider.__name__ in catalog.debug(x)

    @catalog.include
    class DebugYProvider(Provider):
        def can_provide(self, dependency: object) -> bool:
            ...

        def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
            ...

        def maybe_debug(self, dependency: object) -> DependencyDebug | None:
            if dependency is y:
                return DependencyDebug(description=str(dependency), lifetime="transient")
            return None

    @catalog.include
    class NoDebugProvider(Provider, ABC):
        def can_provide(self, dependency: object) -> bool:
            ...

        def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
            ...

        def maybe_debug(self, dependency: object) -> DependencyDebug | None:
            return None

    # Unknown
    assert "Unknown" in catalog.debug(object())
    # x is still unsupported
    assert "No debug provided" in catalog.debug(x)
    assert DummyProvider.__name__ in catalog.debug(x)
    # y
    assert str(y) in catalog.debug(y)

    # error
    @catalog.include
    class DebugErrorProvider(Provider, ABC):
        def can_provide(self, dependency: object) -> bool:
            ...

        def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
            ...

        def maybe_debug(self, dependency: object) -> DependencyDebug | None:
            return object()  # type: ignore

    with pytest.raises(TypeError, match="maybe_debug.*" + DebugErrorProvider.__name__):
        catalog.debug(object())


def test_id(catalog: PublicCatalog, dummy_provider: DummyProvider) -> None:
    assert isinstance(catalog.id, CatalogId)
    assert catalog.private.id != catalog.id
    assert catalog.private.id.name != catalog.id.name
    assert catalog.providers[DummyProvider].catalog.id == catalog.id
    assert catalog.private.providers[DummyProvider].catalog.id == catalog.private.id

    catalog2 = new_catalog(include=[])
    assert catalog2.id != catalog.id
    assert catalog2.private.id != catalog2.id
    assert catalog2.private.id != catalog.private.id


def test_friendly_repr(catalog: PublicCatalog) -> None:
    assert str(catalog.id) in str(catalog)
    assert str(catalog.id) in repr(catalog)
    assert "private" not in repr(catalog).lower()
    assert "private" in repr(catalog.private).lower()

    catalog2 = new_catalog(name="something new", include=[])
    assert "something new" in repr(catalog2)
    assert "something new" in repr(catalog2.private)
    catalog2.include(DummyProvider)


def test_nested_catalog(catalog: PublicCatalog, nested_catalog: PublicCatalog) -> None:
    assert nested_catalog.id != catalog.id

    catalog.include(DummyFactoryProvider)
    dummy_factory_provider = catalog.providers[DummyFactoryProvider]
    dummy_factory_provider.add(x, factory=lambda c: x)

    # does not have any access to the root catalog.
    assert x in catalog
    assert x not in nested_catalog
    # provider wasn't added to nested
    assert DummyFactoryProvider not in nested_catalog.providers

    with pytest.raises(DependencyNotFoundError):
        nested_catalog[x]

    nested_catalog.include(DummyProvider)
    dummy_provider = nested_catalog.providers[DummyProvider]
    dummy_provider.data[y] = y

    # can access nested dependencies
    assert y in nested_catalog
    assert y in catalog
    assert nested_catalog[y] is y
    assert catalog[y] is y
    # but not the nested providers
    assert DummyProvider not in catalog

    assert catalog.debug(y) == nested_catalog.debug(y)

    # Unknown still works
    assert z not in nested_catalog
    assert z not in catalog
    with pytest.raises(DependencyNotFoundError, match=str(z)):
        nested_catalog[z]
    with pytest.raises(DependencyNotFoundError, match=str(z)):
        catalog[z]
    assert "Unknown" in catalog.debug(z)

    # x is unknown for nested
    dummy_provider.data[x] = y
    assert x in nested_catalog
    assert nested_catalog[x] is y
    # catalog's definition has priority
    assert catalog[x] is x

    catalog2 = new_catalog(include=[])
    # cannot be added to a different catalog
    with pytest.raises(ValueError):
        catalog2.include(nested_catalog)


def test_include(catalog: PublicCatalog) -> None:
    def add_dummy(c: Catalog) -> None:
        c.include(DummyProvider)

    assert DummyProvider not in catalog.providers
    catalog.include(add_dummy)
    assert DummyProvider in catalog.providers

    with pytest.raises(TypeError, match="catalog.*function"):
        catalog.include(object())  # type: ignore

    c1 = new_catalog(include=[])
    catalog.include(c1)

    c1.include(DummyProvider)
    c1.providers[DummyProvider].data[x] = x

    assert x in c1
    assert x in catalog
    assert catalog[x] is x
    assert "DummyProvider" in catalog.debug(x)

    c2 = new_catalog(include=[])

    with pytest.raises(ValueError, match=f"parent.*{re.escape(str(catalog.id))}"):
        c2.include(c1)

    with pytest.raises(ValueError, match="(?i)private catalog"):
        catalog.include(c2.private)  # type: ignore


def test_private_access(catalog: PublicCatalog, dummy_provider: DummyProvider) -> None:
    assert catalog.private is not catalog
    assert catalog.private.private is catalog.private

    private_provider = catalog.private.providers[DummyProvider]
    dummy_provider.data[x] = x
    private_provider.data[y] = y

    assert x in catalog
    assert catalog[x] is x
    assert x in catalog.private
    assert catalog.private[x] is x
    assert y not in catalog
    assert y in catalog.private
    assert catalog.private[y] is y


def test_callback(catalog: PublicCatalog) -> None:
    @catalog.include
    class SafeProvider(Provider):
        data: dict[object, Callable[[], object]]
        calls: list[tuple[str, object]]

        def __init__(self, *, catalog: ReadOnlyCatalog) -> None:
            super().__init__(catalog=catalog)
            self.data = {}
            self.calls = []

        def can_provide(self, dependency: object) -> bool:
            return dependency in self.data

        def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
            if dependency in self.data:
                value = self.data[dependency]()
                self.calls.append(("maybe_provide", value))

                def callback() -> object:
                    out = self.data[dependency]()
                    self.calls.append(("safe_provide", out))
                    return out

                out.set_value(
                    value=value,
                    lifetime=LifeTime.TRANSIENT,
                    callback=callback,
                )

    provider = catalog.providers[SafeProvider]
    provider.data[x] = lambda: A()
    assert x in catalog

    a1 = catalog[x]
    a2 = catalog[x]
    a3 = catalog[x]
    assert len({a1, a2, a3}) == 3
    assert provider.calls == [("maybe_provide", a1), ("safe_provide", a2), ("safe_provide", a3)]


def test_catalog_providers(catalog: PublicCatalog) -> None:
    from collections.abc import Mapping

    catalog.include(DummyProvider)

    assert len(catalog.providers) == 1
    assert DummyProvider in catalog.providers
    assert isinstance(catalog.providers[DummyProvider], DummyProvider)
    assert catalog.providers[DummyProvider] is catalog.providers[DummyProvider]
    assert list(catalog.providers) == [DummyProvider]

    catalog.include(DummyFactoryProvider)
    assert len(catalog.providers) == 2

    assert isinstance(catalog.providers, Mapping)


def test_invalid_provider() -> None:
    catalog = new_catalog(include=[DummyFactoryProvider])
    provider = catalog.providers[DummyFactoryProvider]

    @provider.add_raw()
    def double_definition(catalog: ReadOnlyCatalog, out: ProvidedDependency) -> None:
        out.set_value(x, lifetime=LifeTime.SINGLETON)
        out.set_value(x, lifetime=LifeTime.SINGLETON)

    @provider.add_raw()
    def deterministic_without_callback(catalog: ReadOnlyCatalog, out: ProvidedDependency) -> None:
        out.set_value(x, lifetime=LifeTime.SCOPED)

    @provider.add_raw()
    def unknown_scope(catalog: ReadOnlyCatalog, out: ProvidedDependency) -> None:
        out.set_value(x, lifetime="singleton")  # type: ignore

    with pytest.raises(DependencyDefinitionError, match="twice.*dependency value"):
        _ = catalog[double_definition]

    with pytest.raises(DependencyDefinitionError, match="(?i)callback.*bound"):
        _ = catalog[deterministic_without_callback]

    with pytest.raises(TypeError, match="lifetime"):
        _ = catalog[unknown_scope]
