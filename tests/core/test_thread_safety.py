# pyright: reportUnusedClass=false
from __future__ import annotations

import functools
import itertools
import random
import threading
import time
from typing import Callable, Sequence, Tuple, TypeVar

import pytest
from typing_extensions import ParamSpec, TypeAlias

from antidote import antidote_lib, injectable, lazy, ScopeVar
from antidote.core import inject, LifeTime, new_catalog, ProvidedDependency, Provider, PublicCatalog
from tests.conftest import TestContextOf
from tests.utils import Box

T = TypeVar("T")
P = ParamSpec("P")
Tid: TypeAlias = Tuple[int, float]


class ThreadSafetyBench:
    n_threads = 10
    __state = None

    @classmethod
    def run(cls, target: Callable[[], object], n_threads: int | None = None) -> None:
        threads = [threading.Thread(target=target) for _ in range(n_threads or cls.n_threads)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    @staticmethod
    def random_delay(a: float = 0.01, b: float | None = None) -> None:
        b = b or a
        time.sleep(a + b * random.random())

    @staticmethod
    def unique_id() -> Tid:
        return threading.get_ident(), random.random()

    @classmethod
    def check_locked(cls, failures: list[int]) -> None:
        tid = ThreadSafetyBench.unique_id()
        cls.__state = tid
        ThreadSafetyBench.random_delay()
        if cls.__state != tid:
            failures.append(1)


def delayed(f: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(f)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        ThreadSafetyBench.random_delay()
        return f(*args, **kwargs)

    return wrapped


@pytest.mark.timeout(3)
def test_catalog_provide_safety(catalog: PublicCatalog) -> None:
    catalog.include(antidote_lib)

    @injectable(catalog=catalog)
    class A:
        pass

    @injectable(catalog=catalog, lifetime="transient")
    class B:
        pass

    singletons: list[object] = []
    non_singletons: list[object] = []

    def worker() -> None:
        a = catalog[A]
        singletons.append(a)
        non_singletons.append(catalog[B])

    ThreadSafetyBench.run(worker)
    assert len(set(non_singletons)) == ThreadSafetyBench.n_threads
    assert len(set(singletons)) == 1


@pytest.mark.timeout(3)
def test_catalog_scope_consistency(catalog: PublicCatalog) -> None:
    catalog.include(antidote_lib)
    version = ScopeVar(default=ThreadSafetyBench.unique_id(), catalog=catalog)

    @delayed
    def update() -> None:
        version.set(ThreadSafetyBench.unique_id())
        return None

    @lazy(catalog=catalog)
    def f() -> Box[Tuple[Tid, Tid]]:
        v1 = catalog[version]
        ThreadSafetyBench.random_delay()
        v2 = catalog[version]
        return Box((v1, v2))

    actions: list[Callable[[], Box[Tuple[Tid, Tid]] | None]] = [update, lambda: catalog[f()]]
    results: list[Box[Tuple[Tid, Tid]]] = []

    def worker() -> None:
        for f in random.choices(actions, k=30):
            result = f()
            if result is not None:
                results.append(result)

    ThreadSafetyBench.run(worker, n_threads=5)
    for box in results:
        v1, v2 = box.value
        assert v1 is v2


@pytest.mark.timeout(3)
def test_catalog_scoped(catalog: PublicCatalog) -> None:
    catalog.include(antidote_lib)
    version = ScopeVar(default=ThreadSafetyBench.unique_id(), catalog=catalog)

    @delayed
    def update() -> None:
        version.set(ThreadSafetyBench.unique_id())
        return None

    @lazy(catalog=catalog, lifetime="scoped")
    def scoped() -> Box[Tid]:
        return Box(catalog[version])

    dependency = scoped()

    @lazy(catalog=catalog)
    def f() -> Tuple[Box[Tid], Box[Tid]]:
        b1 = catalog[dependency]
        ThreadSafetyBench.random_delay()
        b2 = catalog[dependency]
        return b1, b2

    actions: list[Callable[[], Tuple[Box[Tid], Box[Tid]] | None]] = [update, lambda: catalog[f()]]
    results: list[tuple[Box[Tid], Box[Tid]]] = []

    def worker() -> None:
        for f in random.choices(actions, k=30):
            result = f()
            if result is not None:
                results.append(result)

    ThreadSafetyBench.run(worker, n_threads=5)
    for b1, b2 in results:
        assert b1 is b2

    boxes: list[Box[Tid]] = list(itertools.chain(*([b1, b2] for b1, b2 in results)))
    assert len({box.value for box in boxes}) == len({box for box in boxes})


@pytest.mark.timeout(4)
def test_inject_scoped_consistency(catalog: PublicCatalog) -> None:
    catalog.include(antidote_lib)
    version = ScopeVar(default=ThreadSafetyBench.unique_id(), catalog=catalog)

    @delayed
    def update() -> None:
        version.set(ThreadSafetyBench.unique_id())
        return None

    @lazy(catalog=catalog, lifetime="scoped")
    @delayed
    def f1() -> Box[Tuple[str, Tid]]:
        return Box(("f1", catalog[version]))

    @lazy(catalog=catalog, lifetime="scoped")
    @delayed
    def f2() -> Box[Tuple[str, Tid]]:
        return Box(("f2", catalog[version]))

    @lazy(catalog=catalog, lifetime="scoped")
    @delayed
    def f3() -> Box[Tuple[str, Tid]]:
        return Box(("f3", catalog[version]))

    @inject(catalog=catalog)
    def func(
        a: Box[Tuple[str, Tid]] = inject[f1()],
        b: Box[Tuple[str, Tid]] = inject[f2()],
        c: Box[Tuple[str, Tid]] = inject[f3()],
        d: Box[Tuple[str, Tid]] = inject[f1()],
        e: Box[Tuple[str, Tid]] = inject[f2()],
        f: Box[Tuple[str, Tid]] = inject[f3()],
        g: Box[Tuple[str, Tid]] = inject[f1()],
        h: Box[Tuple[str, Tid]] = inject[f2()],
        i: Box[Tuple[str, Tid]] = inject[f3()],
    ) -> Sequence[Box[Tuple[str, Tid]]]:
        return [a, b, c, d, e, f, g, h, i]

    actions: list[Callable[[], Sequence[Box[Tuple[str, Tid]]] | None]] = [update, func]
    results: list[Sequence[Box[Tuple[str, Tid]]]] = []

    def worker() -> None:
        for f in random.choices(actions, k=20):
            result = f()
            if result is not None:
                results.append(result)

    ThreadSafetyBench.run(worker, n_threads=5)
    for boxes in results:
        assert len(set(boxes)) == 3
        assert len({id(box) for box in boxes}) == 3


@pytest.mark.timeout(3)
def test_catalog_test_safety(test_context_of: TestContextOf) -> None:
    catalog = new_catalog(include=[])
    singletons: list[tuple[Tid, bool]] = []

    def worker() -> None:
        with test_context_of(catalog) as overrides:
            tid = ThreadSafetyBench.unique_id()
            overrides["x"] = tid
            ThreadSafetyBench.random_delay()
            singletons.append((tid, tid == catalog["x"]))

    ThreadSafetyBench.run(worker)
    assert ThreadSafetyBench.n_threads == len({tid for tid, _ in singletons})
    assert all(equal for _, equal in singletons)


@pytest.mark.timeout(2)
def test_unlock_transient_scope() -> None:
    catalog = new_catalog(include=[])
    concurrent_safe_provides: list[int] = []
    concurrent_maybe_provide: list[int] = []

    def callback() -> str:
        ThreadSafetyBench.check_locked(concurrent_safe_provides)
        return "a"

    @catalog.include
    class ProviderA(Provider):
        def can_provide(self, dependency: object) -> bool:
            ...

        def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
            ThreadSafetyBench.check_locked(concurrent_maybe_provide)
            out.set_value("a", lifetime=LifeTime.TRANSIENT, callback=callback)

    def worker() -> None:
        for _ in range(10):
            catalog["a"]

    ThreadSafetyBench.run(worker, n_threads=5)
    assert not concurrent_maybe_provide
    assert concurrent_safe_provides
