from __future__ import annotations

import re
from dataclasses import dataclass

import pytest

from antidote import inject, LifeTime, PublicCatalog, world
from antidote.core import DependencyDebug, ProvidedDependency, Provider, ProviderCatalog
from tests.utils import expected_debug, Obj

x = Obj()
y = Obj()
z = Obj()


class A:
    ...


class B:
    ...


class C:
    ...


class Dummy:
    pass


@dataclass(eq=True, unsafe_hash=True)
class DummyWithRepr:
    message: str = "Hello!"

    def __antidote_debug_repr__(self) -> str:
        return self.message


def dummy_func() -> None:
    ...


class DebugProvider(Provider):
    def __init__(self, *, catalog: ProviderCatalog) -> None:
        super().__init__(catalog=catalog)
        self.data: dict[object, DependencyDebug] = {}

    def maybe_debug(self, dependency: object) -> DependencyDebug | None:
        return self.data.get(dependency)

    def can_provide(self, dependency: object) -> bool:
        raise NotImplementedError()  # pragma: no cover

    def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
        raise NotImplementedError()  # pragma: no cover


dummy = Dummy()


@pytest.mark.parametrize(
    "obj,expected",
    [
        pytest.param(x, repr(x), id="x"),
        (DummyWithRepr(), DummyWithRepr.message),
        pytest.param(dummy, repr(dummy), id="dummy"),
        (DummyWithRepr, "tests.core.test_debug.DummyWithRepr"),
        (Dummy, "tests.core.test_debug.Dummy"),
        (dummy_func, "tests.core.test_debug.dummy_func"),
        (str, "str"),
    ],
)
def test_debug_repr(obj: object, expected: str) -> None:
    with world.test.empty() as overrides:
        overrides[obj] = x
        assert expected in world.debug(obj)


def test_newline_in_debug_repr() -> None:
    @inject(kwargs=dict(x=DummyWithRepr("Hello\nWorld!")))
    def f(x: object) -> None:
        ...

    assert world.debug(f) == expected_debug(
        f"""
    ∅ tests.core.test_debug.{test_newline_in_debug_repr.__name__}.<locals>.f
    └── /!\\ Unknown: Hello
        World!
    """
    )


def test_cyclic_dependency(catalog: PublicCatalog) -> None:
    catalog.include(DebugProvider)
    catalog.providers[DebugProvider].data = {
        A: DependencyDebug(description=str(A), lifetime="transient", dependencies=[B]),
        B: DependencyDebug(description=str(B), lifetime="transient", dependencies=[C]),
        C: DependencyDebug(description=str(C), lifetime="transient", dependencies=[A]),
    }

    assert re.search(f"Cyclic dependency.*{re.escape(str(A))}", catalog.debug(A))
    assert re.search(f"Cyclic dependency.*{re.escape(str(B))}", catalog.debug(B))
    assert re.search(f"Cyclic dependency.*{re.escape(str(C))}", catalog.debug(C))


def test_basic_nested_debug(catalog: PublicCatalog) -> None:
    class D:
        @inject(kwargs=dict(a=x))
        def __init__(self, a: object) -> None:
            ...

    @inject(kwargs=dict(b=y))
    def func(b: object) -> object:
        ...

    sentinel = object()

    catalog.include(DebugProvider)
    catalog.providers[DebugProvider].data = {
        A: DependencyDebug(description=str(A), lifetime="transient", dependencies=[B]),
        B: DependencyDebug(description=str(B), lifetime="transient", wired=[D, func]),
        x: DependencyDebug(description=str(x), lifetime=LifeTime.SINGLETON),
        y: DependencyDebug(description=str(y), lifetime=LifeTime.SCOPED),
        z: DependencyDebug(description=str(z), lifetime="transient", dependencies=[sentinel]),
    }

    # simple debug
    assert str(x) in catalog.debug(x)
    # follows injections
    assert str(x) in catalog.debug(D)
    assert str(y) in catalog.debug(func)
    # follows wired
    assert str(B) in catalog.debug(B)
    assert str(x) in catalog.debug(B)
    assert str(y) in catalog.debug(B)
    # follows dependencies
    assert str(A) in catalog.debug(A)
    assert str(B) in catalog.debug(A)
    assert str(x) in catalog.debug(A)
    assert str(y) in catalog.debug(A)

    # fixed depth
    assert str(B) in catalog.debug(A, depth=2)
    assert str(x) not in catalog.debug(A, depth=2)

    assert re.search(f"Unknown.*{re.escape(str(sentinel))}", catalog.debug(sentinel))
    assert re.search(f"Unknown.*{re.escape(str(sentinel))}", catalog.debug(z))
