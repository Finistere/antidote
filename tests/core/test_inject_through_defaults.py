import sys
from typing import Iterator, Optional, Union

import pytest

from antidote.core import (
    CannotInferDependencyError,
    DependencyNotFoundError,
    dependencyOf,
    inject,
    world,
)
from tests.utils import Obj

x = Obj()


class A(Obj):
    ...


class B(Obj):
    ...


@pytest.fixture(autouse=True)
def setup_world() -> Iterator[None]:
    with world.test.empty() as overrides:
        overrides[A] = A()
        yield


def test_inject_me() -> None:
    @inject
    def f1(a: A = inject.me()) -> A:
        return a

    assert f1() is world[A]

    @inject
    def f2(a: A = inject[A]) -> A:
        return a

    assert f2() is world[A]

    @inject
    def f3(a: Optional[A] = inject.get(A)) -> A:
        assert a is not None
        return a

    assert f3() is world[A]

    @inject
    def f4(a: A = inject[A]) -> A:
        return a

    assert f4() is world[A]


def test_inject_me_dependency_not_found() -> None:
    @inject
    def f(b: B = inject.me()) -> B:
        ...

    # Should not fail before.
    with pytest.raises(DependencyNotFoundError):
        f()


def test_inject_me_missing_type_hint() -> None:
    with pytest.raises(CannotInferDependencyError, match=r"(?i).*inject\.me.*"):

        @inject
        def f(my_service=inject.me()) -> None:  # type: ignore
            ...


def test_inject_me_optional() -> None:
    @inject
    def f(a: Optional[A] = inject.me()) -> Optional[A]:
        return a

    assert f() is world[A]

    with world.test.empty():
        assert f() is None

    @inject
    def f2(a: Union[A, None] = inject.me()) -> Union[A, None]:
        return a

    assert f2() is world[A]

    with world.test.empty():
        assert f2() is None

    @inject
    def f2b(a: Union[None, A] = inject.me()) -> Union[None, A]:
        return a

    assert f2b() is world[A]

    with world.test.empty():
        assert f2b() is None

    if sys.version_info >= (3, 10):

        @inject
        def f3(a: "A | None" = inject.me()) -> "A | None":
            return a

        assert f3() is world[A]

        with world.test.empty():
            assert f3() is None

        @inject
        def f3b(a: "None | A" = inject.me()) -> "None | A":
            return a

        assert f3b() is world[A]

        with world.test.empty():
            assert f3b() is None


def test_inject_get() -> None:
    @inject
    def f(a: object = inject[A]) -> object:
        return a

    assert f() is world[A]

    @inject
    def f2(a: object = dependencyOf(A)) -> object:
        return a

    assert f2() is world[A]


def test_inject_get_default() -> None:
    sentinel_a = A()
    sentinel_b = B()

    @inject
    def f(a: object = inject.get(A, default=sentinel_a)) -> object:
        return a

    @inject
    def g(b: object = inject.get(B, default=sentinel_b)) -> object:
        return b

    assert f() is world[A]
    assert g() is sentinel_b

    @inject
    def f2(a: object = dependencyOf(A, default=x)) -> object:
        return a

    @inject
    def g2(b: object = dependencyOf(B, default=sentinel_b)) -> object:
        return b

    assert f2() is world[A]
    assert g2() is sentinel_b


def test_inject_get_dependency_not_found() -> None:
    @inject
    def f(b: object = inject[B]) -> object:
        ...

    # Should not fail before.
    with pytest.raises(DependencyNotFoundError):
        f()

    @inject
    def f2(b: object = dependencyOf(B)) -> object:
        ...

    # Should not fail before.
    with pytest.raises(DependencyNotFoundError):
        f2()
