# pyright: reportUnusedFunction=false
from __future__ import annotations

import itertools
import re
from typing import Any, cast, TypeVar

import pytest
from typing_extensions import ContextManager

from antidote.core import inject, new_catalog, PublicCatalog
from tests.conftest import TestContextOf
from tests.core.dummy_providers import DummyFactoryProvider, DummyProvider
from tests.utils import Obj

T = TypeVar("T")


def _(x: T) -> T:
    return x


x = Obj()
y = Obj()
z = Obj()


def test_empty_override(catalog: PublicCatalog, nested_catalog: PublicCatalog) -> None:
    catalog.include(DummyProvider)
    original = catalog.providers[DummyProvider]
    original.data = {x: x}
    nested_catalog.include(DummyFactoryProvider)
    nested_catalog.providers[DummyFactoryProvider].add(z, factory=lambda c: object())
    z_value = nested_catalog[z]

    with catalog.test.empty():
        # Old providers not present
        assert DummyProvider not in catalog.providers
        # Can add providers
        catalog.include(DummyFactoryProvider)
        assert DummyFactoryProvider in catalog.providers

        # Adding a singleton
        catalog.providers[DummyFactoryProvider].add(x, factory=lambda _: object())
        xx = catalog[x]
        assert catalog[x] is xx

        # didn't change nested_catalog
        assert z in nested_catalog
        assert nested_catalog[z] is z_value
        assert DummyFactoryProvider in nested_catalog.providers

        # not in catalog anymore
        assert z not in catalog

    # Unchanged original
    assert catalog.providers[DummyProvider] is original
    assert DummyFactoryProvider not in catalog.providers
    assert catalog[x] is x


def test_new_override(catalog: PublicCatalog) -> None:
    catalog.include(DummyFactoryProvider)
    dummy_provider = catalog.providers[DummyFactoryProvider]
    dummy_provider.add(x, factory=lambda c: object(), lifetime="singleton")
    x_value = catalog[x]  # retrieve singleton

    with catalog.test.new():
        assert DummyFactoryProvider not in catalog.providers
        assert list(catalog.providers.keys()) == list(new_catalog().providers.keys())

        catalog.include(DummyFactoryProvider)
        catalog.providers[DummyFactoryProvider].add(
            x, factory=lambda c: object(), lifetime="singleton"
        )
        assert catalog[x] is not x_value

    with catalog.test.new(include=[DummyProvider]):
        assert DummyProvider in catalog.providers
        assert list(catalog.providers.keys()) == [DummyProvider]

    # Unchanged original
    assert len(catalog.providers) == 1
    assert catalog.providers[DummyFactoryProvider] is dummy_provider
    assert catalog[x] is x_value


@pytest.mark.parametrize("copy, frozen", list(itertools.product([True, False], repeat=2)))
def test_clone_override(
    catalog: PublicCatalog, nested_catalog: PublicCatalog, copy: bool, frozen: bool
) -> None:
    catalog.include(DummyFactoryProvider)
    original = catalog.providers[DummyFactoryProvider]
    original.add(x, factory=lambda _: object())
    nested_catalog.include(DummyFactoryProvider)
    nested_catalog.providers[DummyFactoryProvider].add(z, factory=lambda c: object())
    z_value = nested_catalog[z]
    x_value = catalog[x]
    debug_info = catalog.debug(x)

    context: ContextManager[Any] = (
        catalog.test.copy(frozen=frozen) if copy else catalog.test.clone(frozen=frozen)
    )
    with context:
        assert catalog.is_frozen == frozen
        assert DummyFactoryProvider in catalog.providers
        assert isinstance(catalog.providers[DummyFactoryProvider], DummyFactoryProvider)
        assert catalog.providers[DummyFactoryProvider] is not original
        assert (catalog.get(x, default=object()) is x_value) == copy

        if copy:
            assert catalog.debug(x) == debug_info

        if not frozen:
            catalog.include(DummyProvider)
            catalog.providers[DummyProvider].data = {y: y}
            assert y in catalog
            assert catalog[y] is y
            catalog.freeze()
            assert catalog.is_frozen

        # nested still in catalog, with a copy of the children.
        assert z in catalog
        assert DummyFactoryProvider in nested_catalog.providers
        if copy:
            assert catalog[z] is z_value
            assert nested_catalog[z] is z_value
        else:
            value = catalog[z]
            assert value is not z_value
            assert catalog[z] is value
            assert nested_catalog[z] is value

    assert not catalog.is_frozen
    assert DummyProvider not in catalog
    assert y not in catalog
    assert catalog[x] is x_value
    assert catalog.providers[DummyFactoryProvider] is original


def test_override_independent(catalog: PublicCatalog, test_context_of: TestContextOf) -> None:
    catalog.include(DummyProvider)
    catalog.providers[DummyProvider].data = {x: x}

    # __setitem__
    with test_context_of(catalog) as overrides:
        overrides[z] = z
        assert z in catalog
        assert catalog[z] == z

        overrides[x] = y
        assert x in catalog
        assert catalog[x] is y

    # back to normal
    assert catalog[x] is x
    assert z not in catalog
    assert catalog.get(z) is None

    # update
    with test_context_of(catalog) as overrides:
        overrides.update({x: y, z: z})
        assert z in catalog
        assert catalog[z] == z
        assert x in catalog
        assert catalog[x] == y

    assert catalog[x] is x
    assert z not in catalog
    assert catalog.get(z) is None

    # factory
    with test_context_of(catalog) as overrides:

        @overrides.factory(x)
        def create() -> object:
            return object()

        assert x in catalog
        assert catalog[x] is not x
        assert catalog[x] is not catalog[x]

        @overrides.factory(y, singleton=True)
        def create2() -> object:
            return object()

        assert y in catalog
        assert catalog[y] is catalog[y]

    # __delitem__
    with test_context_of(catalog) as overrides:
        del overrides[x]
        assert x not in catalog
        assert catalog.get(x) is None

        # should not fail
        del overrides[y]
        del overrides[z]

        assert z not in catalog
        assert catalog.get(z) is None

        if DummyProvider in catalog.providers:
            catalog.providers[DummyProvider].data = {z: z}
            assert z not in catalog
            assert catalog.get(z) is None

        # reversible with an overrides
        overrides[x] = z

        @overrides.factory(y)
        def create3() -> object:
            return y

        overrides.update({z: x})

        assert x in catalog
        assert catalog[x] is z
        assert y in catalog
        assert catalog[y] is y
        assert z in catalog
        assert catalog[z] is x

        # deleting all overrides
        del overrides[x]
        del overrides[y]
        del overrides[z]

        assert x not in catalog
        assert catalog.get(x) is None
        assert y not in catalog
        assert catalog.get(y) is None
        assert z not in catalog
        assert catalog.get(z) is None

    assert catalog[x] is x

    assert z not in catalog
    assert catalog.get(z) is None
    assert y not in catalog
    assert catalog.get(y) is None


def test_nested_overrides(catalog: PublicCatalog) -> None:
    catalog.include(DummyProvider)
    catalog.providers[DummyProvider].data = {x: x}
    a = object()
    b = object()

    with catalog.test.copy() as overrides:
        overrides[y] = y

        @overrides.factory(z, singleton=True)
        def create() -> object:
            return object()

        original_z = catalog[z]

        with catalog.test.clone() as nested:
            assert y not in catalog
            assert catalog.get(y) is None
            assert z in catalog
            assert catalog[z] is not original_z

            nested[y] = object()

            with pytest.raises(RuntimeError):
                overrides[a] = b

            assert a not in catalog
            assert catalog.get(a) is None

            nested[a] = a
            assert a in catalog
            assert catalog[a] is a

        assert a not in catalog
        assert catalog[y] is y
        assert catalog[z] is original_z

        with catalog.test.copy() as nested:
            assert y in catalog
            assert catalog[y] is y
            assert z in catalog
            assert catalog[z] is original_z

            nested_z = object()
            nested[z] = nested_z
            assert catalog[z] is nested_z

        assert catalog[z] is original_z


def test_debug(catalog: PublicCatalog, test_context_of: TestContextOf) -> None:
    with test_context_of(catalog) as overrides:
        overrides[x] = x

        @overrides.factory(y)
        def create() -> object:
            ...

        assert f"Override/Singleton: {x!r} -> {x!r}" in catalog.debug(x)
        assert (
            f"Override/Factory: {y!r} -> "
            f"tests.core.test_catalog_overrides.test_debug.<locals>.create" in catalog.debug(y)
        )
        assert "Unknown" in catalog.debug(object())

        if not catalog.is_frozen:
            catalog.include(DummyProvider)
            catalog.providers[DummyProvider].data = {z: z}
            assert "No debug provided" in catalog.debug(z)

        with catalog.test.copy() as nested:
            del nested[x]
            del nested[y]
            del nested[z]

            assert "Unknown" in catalog.debug(x)
            assert "Unknown" in catalog.debug(y)
            assert "Unknown" in catalog.debug(z)


def test_provider_error(catalog: PublicCatalog, test_context_of: TestContextOf) -> None:
    with test_context_of(catalog) as overrides:

        @overrides.factory(x)
        def fx() -> object:
            raise RuntimeError("Hello!")

        with pytest.raises(RuntimeError, match="Hello!"):
            catalog[x]


def test_id(catalog: PublicCatalog, test_context_of: TestContextOf) -> None:
    current_id = catalog.id
    current_private_id = catalog.private.id

    with test_context_of(catalog):
        assert catalog.id.name == current_id.name
        assert catalog.id.test_env != current_id.test_env
        assert catalog.private.id.name == current_private_id.name
        assert catalog.private.id.test_env != current_private_id.test_env


def test_private(catalog: PublicCatalog, test_context_of: TestContextOf) -> None:
    with test_context_of(catalog) as overrides:
        if not catalog.is_frozen:
            catalog.include(DummyProvider)
            assert DummyProvider in catalog.providers
            assert DummyProvider in catalog.private.providers

        overrides[x] = x
        assert x in catalog
        assert x in catalog.private
        assert catalog[x] is x
        assert catalog.private[x] is x

        overrides.of(catalog.private)[y] = y
        assert y not in catalog
        assert y in catalog.private
        assert catalog.private[y] is y

    assert DummyProvider not in catalog.providers
    assert DummyProvider not in catalog.private.providers


def test_children_overrides(
    catalog: PublicCatalog, test_context_of: TestContextOf, nested_catalog: PublicCatalog
) -> None:
    catalog.include(DummyProvider)
    nested_catalog.include(DummyProvider)
    nested_catalog.providers[DummyProvider].data[z] = z

    with test_context_of(catalog):
        # If provider isn't kept catalog children won't either, so nothing to test.
        if DummyProvider not in catalog.providers:
            return

    c1 = new_catalog(include=[])

    with test_context_of(catalog) as overrides:
        with pytest.raises(TypeError):
            overrides.of(object())  # type: ignore
        with pytest.raises(LookupError, match=re.escape(repr(c1))):
            overrides.of(c1)

        overrides[x] = x
        assert x in catalog
        assert x not in nested_catalog

        overrides.of(nested_catalog)[y] = y
        assert y in nested_catalog
        assert y in catalog
        assert catalog[y] is y
        assert nested_catalog[y] is y

    with test_context_of(catalog) as overrides:

        @_(overrides.of(nested_catalog).factory(x))
        def create_x() -> object:
            return [x]

        assert x in nested_catalog
        assert x in catalog
        assert nested_catalog[x] == [x]
        assert catalog[x] == [x]
        assert catalog[x] is not nested_catalog[x]

    with test_context_of(catalog) as overrides:

        @_(overrides.of(nested_catalog).factory(x, singleton=True))
        def create_x2() -> object:
            return [x]

        assert x in nested_catalog
        assert x in catalog
        assert nested_catalog[x] == [x]
        assert catalog[x] is nested_catalog[x]

    with test_context_of(catalog) as overrides:
        overrides.of(nested_catalog)[y] = y
        assert y in nested_catalog

        del overrides.of(nested_catalog)[y]
        assert y not in nested_catalog

        # Some contexts will keep z
        del overrides.of(nested_catalog)[z]
        assert z not in nested_catalog

    with test_context_of(catalog) as overrides:
        overrides.of(nested_catalog).update({x: x})
        assert x in nested_catalog
        assert x in catalog
        assert catalog[x] is x
        assert nested_catalog[x] is x


def test_factory_injection(catalog: PublicCatalog, test_context_of: TestContextOf) -> None:
    with test_context_of(catalog) as overrides:
        overrides["name"] = "world"

        @overrides.factory("greeting")
        def greeting(name: str = cast(str, inject["name"])) -> str:
            return f"Hello {name}!"

        assert catalog["greeting"] == "Hello world!"

        @overrides.factory("greeting2")
        @inject(dict(name="name"))
        def greeting2(name: str = "") -> str:
            return f"Hello {name}!"

        assert catalog["greeting2"] == "Hello world!"


def test_overrides_update(catalog: PublicCatalog, test_context_of: TestContextOf) -> None:
    with test_context_of(catalog) as overrides:
        with pytest.raises(TypeError, match="dictionary or iterable"):
            overrides.update(object(), object())  # type: ignore

        with pytest.raises(TypeError, match="iterable"):
            overrides.update(object())  # type: ignore

        overrides.update(x=x)
        assert "x" in catalog
        assert catalog["x"] is x

        overrides.update({x: x})
        assert x in catalog
        assert catalog[x] is x

        overrides.update([(y, x)])
        assert y in catalog
        assert catalog[y] is x
