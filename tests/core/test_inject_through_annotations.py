# pyright: reportUnusedFunction=false
import sys
from typing import Iterator, Optional, Union

import pytest
from typing_extensions import Annotated

from antidote import (
    CannotInferDependencyError,
    DependencyNotFoundError,
    dependencyOf,
    inject,
    InjectMe,
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


def test_annotations_inject() -> None:
    @inject
    def f(a: InjectMe[A]) -> A:
        return a

    assert f() is world[A]  # type: ignore


def test_annotations_inject_dependency_not_found() -> None:
    @inject
    def f(a: InjectMe[B]) -> object:
        ...

    with pytest.raises(DependencyNotFoundError):
        f()  # type: ignore


def test_annotations_inject_optional() -> None:
    @inject
    def f(a: InjectMe[Optional[A]] = None) -> Optional[A]:
        return a

    assert f() is world[A]
    with world.test.empty():
        assert f() is None

    @inject
    def f2(a: InjectMe[Union[A, None]] = None) -> Union[A, None]:
        return a

    assert f2() is world[A]
    with world.test.empty():
        assert f2() is None

    @inject
    def f2b(a: InjectMe[Union[None, A]] = None) -> Union[None, A]:
        return a

    assert f2b() is world[A]
    with world.test.empty():
        assert f2b() is None

    if sys.version_info >= (3, 10):

        @inject
        def f3(a: "InjectMe[A | None]" = None) -> "A | None":
            return a

        assert f3() is world[A]
        with world.test.empty():
            assert f3() is None

        @inject
        def f3b(a: "InjectMe[None | A]" = None) -> "None | A":
            return a

        assert f3b() is world[A]
        with world.test.empty():
            assert f3b() is None


def test_annotations_get() -> None:
    @inject
    def f(a: Annotated[object, dependencyOf(A)] = object()) -> object:
        return a

    assert f() is world[A]

    @inject
    def f2(a: Annotated[object, inject[A]] = object()) -> object:
        return a

    assert f2() is world[A]


def test_annotations_get_default() -> None:
    sentinel_a = A()
    sentinel_b = B()

    @inject
    def f(a: Annotated[object, dependencyOf(A, default=sentinel_a)] = object()) -> object:
        return a

    @inject
    def g(b: Annotated[object, dependencyOf(B, default=sentinel_b)] = object()) -> object:
        return b

    assert f() is world[A]
    assert g() is sentinel_b

    @inject
    def f2(a: Annotated[object, inject.get(A, default=sentinel_a)] = object()) -> object:
        return a

    @inject
    def g2(b: Annotated[object, inject.get(B, default=sentinel_b)] = object()) -> object:
        return b

    assert f2() is world[A]
    assert g2() is sentinel_b


def test_annotations_get_dependency_not_found() -> None:
    @inject
    def f(a: Annotated[A, dependencyOf(B)]) -> A:
        ...

    with pytest.raises(DependencyNotFoundError):
        f()  # type: ignore

    @inject
    def f2(a: Annotated[A, inject[B]]) -> A:
        ...

    with pytest.raises(DependencyNotFoundError):
        f2()  # type: ignore


def test_implicit_optional() -> None:
    @inject
    def f(a: Annotated[object, dependencyOf(A)] = None) -> object:
        return a

    assert f() is world[A]

    @inject
    def f2(a: Annotated[object, inject[A]] = None) -> object:
        return a

    assert f2() is world[A]

    @inject
    def f3(a: InjectMe[A] = None) -> object:  # type: ignore
        return a

    assert f3() is world[A]


def test_invalid_multiple_annotations() -> None:
    annotation = dependencyOf[object](A)

    with pytest.raises(CannotInferDependencyError, match="(?i)multiple.*annotations"):

        @inject
        def f(a: Annotated[object, annotation, annotation]) -> None:
            ...

    with pytest.raises(CannotInferDependencyError, match="(?i)multiple.*annotations"):

        @inject
        def f2(a: Annotated[object, dependencyOf(A), dependencyOf(B)]) -> None:
            ...


def test_cannot_use_with_default_dependency() -> None:
    with pytest.raises(
        CannotInferDependencyError, match="(?i)both a default dependency and a annotated dependency"
    ):

        @inject
        def f(a: Annotated[object, dependencyOf(A)] = dependencyOf(A)) -> object:
            ...
