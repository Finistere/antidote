from dataclasses import dataclass
from typing import Any, Iterator, Optional

import pytest
from typing_extensions import Annotated

from antidote import inject, world
from antidote.core import Dependency
from antidote.core.data import dependencyOf, ParameterDependency
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


def test_custom_dependency() -> None:
    class Dummy(Dependency[object]):
        def __antidote_dependency_hint__(self) -> object:
            return A

    @inject
    def f(a: object = Dummy()) -> object:
        return a

    assert f() is world[A]

    @inject
    def g(a: Annotated[object, Dummy()] = object()) -> object:
        return a

    assert g() is world[A]


def test_custom_parameter_dependency() -> None:
    class Dummy(ParameterDependency):
        def __antidote_parameter_dependency__(
            self, *, name: str, type_hint: object, type_hint_with_extras: object
        ) -> Dependency[Any]:
            return dependencyOf(A)

    @inject
    def f(a: object = Dummy()) -> object:
        return a

    assert f() is world[A]

    @inject
    def g(a: Annotated[object, Dummy()] = object()) -> object:
        return a

    assert g() is world[A]


def test_parameter_dependency_proper_parameters() -> None:
    @dataclass
    class Params:
        name: str
        type_hint: object
        type_hint_with_extras: object

    class Dep(ParameterDependency):
        def __antidote_parameter_dependency__(
            self, *, name: str, type_hint: object, type_hint_with_extras: object
        ) -> Dependency[Any]:
            return dependencyOf(object(), default=Params(name, type_hint, type_hint_with_extras))

    @inject
    def f(a=Dep()) -> object:  # type: ignore
        return a

    assert f() == Params("a", None, None)

    @inject
    def f2(a: object = Dep()) -> object:
        return a

    assert f2() == Params("a", object, object)

    @inject
    def f3(hello: object = Dep()) -> object:
        return hello

    assert f3() == Params("hello", object, object)

    @inject
    def f4(a: Optional[Dep] = Dep()) -> object:
        return a

    assert f4() == Params("a", Optional[Dep], Optional[Dep])

    @inject
    def f5(a: Annotated[Dep, 123] = Dep()) -> object:
        return a

    assert f5() == Params("a", Dep, Annotated[Dep, 123])

    dep = Dep()

    @inject
    def g(a: Annotated[object, dep] = object()) -> object:
        return a

    assert g() == Params("a", object, Annotated[object, dep])

    @inject
    def g2(hello: Annotated[object, dep] = object()) -> object:
        return hello

    assert g2() == Params("hello", object, Annotated[object, dep])

    @inject
    def g3(a: Annotated[Optional[int], dep] = 32) -> object:
        return a

    assert g3() == Params("a", Optional[int], Annotated[Optional[int], dep])
