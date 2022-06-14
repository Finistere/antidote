from dataclasses import dataclass
from typing import Generic, TypeVar

import pytest

from antidote._internal import Default
from antidote.core import Dependency, DependencyDebug, dependencyOf
from antidote.core.data import DebugInfoPrefix, LifeTime, ParameterDependency

T = TypeVar("T")

x = object()
y = object()
z = object()


def test_scope() -> None:
    assert LifeTime.of("transient") is LifeTime.TRANSIENT
    assert LifeTime.of("scoped") is LifeTime.SCOPED
    assert LifeTime.of("singleton") is LifeTime.SINGLETON
    assert LifeTime.of(LifeTime.TRANSIENT) is LifeTime.TRANSIENT
    assert LifeTime.of(LifeTime.SCOPED) is LifeTime.SCOPED
    assert LifeTime.of(LifeTime.SINGLETON) is LifeTime.SINGLETON

    with pytest.raises(TypeError, match="lifetime"):
        LifeTime.of(object())  # type: ignore


def test_dependency_debug() -> None:
    dd = DependencyDebug(description="Hello World!", lifetime="transient")
    assert dd.description == "Hello World!"
    assert dd.lifetime is LifeTime.TRANSIENT
    assert not dd.wired
    assert not dd.dependencies

    ref = DependencyDebug(description="info", lifetime="transient", wired=[1], dependencies=[2])
    assert ref == DependencyDebug(
        description="info", lifetime="transient", wired=[1], dependencies=[2]
    )
    assert ref != DependencyDebug(
        description="info2", lifetime="transient", wired=[1], dependencies=[2]
    )
    assert ref != DependencyDebug(
        description="info", lifetime=LifeTime.SINGLETON, wired=[1], dependencies=[2]
    )
    assert ref != DependencyDebug(
        description="info", lifetime="transient", wired=[10], dependencies=[2]
    )
    assert ref != DependencyDebug(
        description="info", lifetime="transient", wired=[1], dependencies=[20]
    )

    with pytest.raises(TypeError, match="description"):
        DependencyDebug(description=object(), lifetime="transient")  # type: ignore

    with pytest.raises(TypeError, match="lifetime"):
        DependencyDebug(description="", lifetime=object())  # type: ignore

    with pytest.raises(TypeError, match="wired"):
        DependencyDebug(description="", lifetime="transient", wired=object())  # type: ignore

    with pytest.raises(TypeError, match="dependencies"):
        DependencyDebug(description="", lifetime="transient", dependencies=object())  # type: ignore


def test_debug_prefix() -> None:
    dip = DebugInfoPrefix(prefix="prefix", dependency=x)
    assert dip.prefix == "prefix"
    assert dip.dependency is x
    assert dip == DebugInfoPrefix(prefix="prefix", dependency=x)
    assert dip != DebugInfoPrefix(prefix="different", dependency=x)
    assert dip != DebugInfoPrefix(prefix="prefix", dependency=object())

    with pytest.raises(TypeError, match="prefix"):
        DebugInfoPrefix(prefix=object(), dependency=object)  # type: ignore


class Simple(Dependency[object]):
    pass


@dataclass
class Nested(Dependency[object]):
    dependency: object

    def __antidote_dependency_hint__(self) -> object:
        return self.dependency


def test_dependency() -> None:
    dummy = Simple()
    assert dummy.__antidote_dependency_hint__() is dummy


def test_get() -> None:
    assert issubclass(dependencyOf, Dependency)

    dep = dependencyOf[object](x)
    assert dep.wrapped is x
    assert dep.default is Default.sentinel
    assert dep == dependencyOf(x)
    assert dep != dependencyOf(y)
    assert dep != dependencyOf(x, default=y)
    assert dependencyOf(x, default=y) == dependencyOf(x, default=y)
    assert dependencyOf(x, default=y) != dependencyOf(x, default=z)


simple = Simple()


class DummyGeneric(Generic[T]):
    pass


@pytest.mark.parametrize(
    "expected,value",
    [
        # sanity checks
        pytest.param(dependencyOf[object](x), dependencyOf[object](x), id="sanity-1"),
        pytest.param(
            dependencyOf[object](x, default=y), dependencyOf[object](x, default=y), id="sanity-2"
        ),
        # proper unwrapping
        pytest.param(dependencyOf[object](x), dependencyOf[object](Nested(x)), id="unwrap-1"),
        pytest.param(
            dependencyOf[object](x), dependencyOf[object](Nested(Nested(x))), id="unwrap-2"
        ),
        pytest.param(
            dependencyOf[object](x),
            dependencyOf[object](Nested(dependencyOf[object](x))),
            id="unwrap-3",
        ),
        pytest.param(
            dependencyOf[object](x), dependencyOf[object](dependencyOf[object](x)), id="unwrap-4"
        ),
        pytest.param(
            dependencyOf[object](simple),
            dependencyOf[object](Nested(simple)),
            id="unwrap-fixed-point-1",
        ),
        pytest.param(
            dependencyOf[object](x, default=y),
            dependencyOf[object](dependencyOf[object](x, default=y)),
            id="default-1",
        ),
        pytest.param(
            dependencyOf[object](x, default=z),
            dependencyOf[object](dependencyOf[object](x, default=y), default=z),
            id="default-2",
        ),
        pytest.param(
            dependencyOf[object](x, default=y),
            dependencyOf[object](Nested(dependencyOf[object](x, default=y))),
            id="default-3",
        ),
        pytest.param(
            dependencyOf[object](x, default=z),
            dependencyOf[object](Nested(dependencyOf[object](x, default=y)), default=z),
            id="default-4",
        ),
        pytest.param(
            dependencyOf[object](DummyGeneric[int]),
            dependencyOf[object](DummyGeneric[int]),
            id="generic",
        ),
    ],
)
def test_get_dependency_unwrap(expected: dependencyOf[object], value: dependencyOf[object]) -> None:
    assert value == expected


def test_parameter_dependency() -> None:
    with pytest.raises(TypeError, match="__antidote_parameter_dependency__"):

        class Dummy(ParameterDependency):
            pass

        Dummy()  # type: ignore

    class Impl(ParameterDependency):
        def __antidote_parameter_dependency__(
            self, *, name: str, type_hint: object, type_hint_with_extras: object
        ) -> Dependency[object]:
            return super().__antidote_parameter_dependency__(
                name=name, type_hint=type_hint, type_hint_with_extras=type_hint_with_extras
            )

    with pytest.raises(NotImplementedError):
        Impl().__antidote_parameter_dependency__(
            name="", type_hint=None, type_hint_with_extras=None
        )
