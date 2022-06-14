# pyright: reportUnusedClass=false, reportUnusedFunction=false
import os

import pytest

from antidote import antidote_injectable, injectable, interface, is_compiled, lazy, new_catalog
from antidote.core import is_catalog, MissingProviderError, world


def test_create_catalog() -> None:
    catalog = new_catalog()
    assert len(catalog.providers) > 0

    # All kinds of dependencies should be available by default:
    @interface(catalog=catalog)
    class Base:
        pass

    @injectable(catalog=catalog)
    class Dummy:
        pass

    @lazy(catalog=catalog)
    def f() -> None:
        ...

    emtpy_catalog = new_catalog(name="empty", include=[])
    assert len(emtpy_catalog.providers) == 0
    assert "empty" in str(emtpy_catalog)
    assert "empty" in emtpy_catalog.id.name

    injectable_catalog = new_catalog(include=[antidote_injectable])
    assert len(injectable_catalog.providers) == 1

    # should work
    @injectable(catalog=injectable_catalog)
    class Dummy2:
        pass

    with pytest.raises(MissingProviderError):

        @interface(catalog=injectable_catalog)
        class Base2:
            pass

    with pytest.raises(ValueError, match="name"):
        new_catalog(name="#")

    with pytest.raises(TypeError, match="name"):
        new_catalog(name=object())  # type: ignore


def test_is_catalog() -> None:
    assert is_catalog(world)
    assert is_catalog(new_catalog())


def test_is_compiled() -> None:
    assert isinstance(is_compiled(), bool)
    assert is_compiled() == (os.environ.get("ANTIDOTE_COMPILED") == "true")
