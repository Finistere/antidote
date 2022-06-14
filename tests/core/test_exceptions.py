from typing import Callable, cast, List

from antidote import new_catalog
from antidote.core import (
    AntidoteError,
    DependencyNotFoundError,
    DoubleInjectionError,
    DuplicateDependencyError,
    FrozenCatalogError,
    PublicCatalog,
)

to_str = cast(List[Callable[[object], str]], [str, repr])


def test_dependency_not_found(catalog: PublicCatalog) -> None:
    o = object()
    error = DependencyNotFoundError(o, catalog=catalog)
    assert isinstance(error, AntidoteError)

    for f in to_str:
        assert repr(o) in f(error)
        assert str(catalog.id) in f(error)


def test_duplicate_dependency_error() -> None:
    message = "hello"
    error = DuplicateDependencyError(message)
    assert isinstance(error, AntidoteError)
    assert message in str(error)


def test_frozen_world() -> None:
    catalog = new_catalog()
    error = FrozenCatalogError(catalog)
    assert isinstance(error, AntidoteError)
    assert str(catalog) in str(error)
    assert str(catalog) in repr(error)


def test_duplicate_dependency() -> None:
    x = object()
    y = object()
    error = DuplicateDependencyError(x, y)
    assert isinstance(error, AntidoteError)
    for f in to_str:
        assert f(x) in f(error)
        assert f(y) in f(error)

    message = "test"
    error = DuplicateDependencyError(message)
    assert str(message) in str(error)
    assert str(message) in repr(error)


def test_double_injection_error() -> None:
    x = object()
    error = DoubleInjectionError(x)
    assert isinstance(error, AntidoteError)
    assert str(x) in str(error)
