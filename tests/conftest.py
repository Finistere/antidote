from __future__ import annotations

from typing import Any, Callable, ContextManager, Iterator

import pytest
from typing_extensions import TypeAlias

from antidote import config, is_compiled, world
from antidote.core import CatalogOverrides, new_catalog, PublicCatalog

TestContextOf: TypeAlias = Callable[[PublicCatalog], ContextManager[CatalogOverrides]]
config.auto_detect_type_hints_locals = True


def pytest_runtest_setup(item: Any) -> None:
    if any(mark.name == "compiled_only" for mark in item.iter_markers()):
        if not is_compiled():
            pytest.skip("Compiled only test.")


@pytest.fixture(autouse=True)
def auto_empty_world() -> Iterator[None]:
    with world.test.empty():
        yield


@pytest.fixture
def clean_config() -> Iterator[None]:
    config.auto_detect_type_hints_locals = False
    yield
    config.auto_detect_type_hints_locals = True


@pytest.fixture(params=["create", "test"])
def catalog(request: Any) -> Iterator[PublicCatalog]:
    c = new_catalog(include=[])
    if request.param == "create":
        yield c
    else:
        with c.test.empty():
            yield c


@pytest.fixture(params=["nested", "deep-nested"])
def nested_catalog(catalog: PublicCatalog, request: Any) -> PublicCatalog:
    c1 = new_catalog(name="nested", include=[])
    catalog.include(c1)
    if request.param == "nested":
        return c1
    else:
        c2 = new_catalog(name="deep-nested", include=[])
        c1.include(c2)
        return c2


def _test_param(func: TestContextOf, *, id: str) -> object:
    return pytest.param(func, id=id)


@pytest.fixture(
    params=[
        _test_param(lambda c: c.test.empty(), id="empty"),
        _test_param(lambda c: c.test.new(), id="new"),
        _test_param(lambda c: c.test.clone(frozen=False), id="clone(frozen=False)"),
        _test_param(lambda c: c.test.clone(frozen=True), id="clone(frozen=True)"),
        _test_param(lambda c: c.test.copy(frozen=False), id="copy(frozen=False)"),
        _test_param(lambda c: c.test.copy(frozen=True), id="copy(frozen=True)"),
    ]
)
def test_context_of(request: object) -> TestContextOf:
    return request.param  # type: ignore
