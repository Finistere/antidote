# pyright: reportUnusedClass=false
from __future__ import annotations

from typing import Iterator

import pytest

from antidote import inject, Inject, injectable, Service, Wiring, world
from antidote.core.exceptions import DuplicateDependencyError
from antidote.lib.injectable import register_injectable_provider


@pytest.fixture(autouse=True)
def setup_world() -> Iterator[None]:
    with world.test.empty():
        register_injectable_provider()
        yield


def test_simple() -> None:
    @injectable
    class Dummy:
        pass

    dummy = world.get(Dummy)
    assert isinstance(dummy, Dummy)
    # Singleton by default
    assert world.get(Dummy) is dummy

    @inject
    def f(x: Dummy = inject.me()) -> Dummy:
        return x

    assert f() is dummy

    @inject
    def f2(x: Dummy = inject.get(Dummy)) -> Dummy:
        return x

    assert f2() is dummy


def test_singleton() -> None:
    @injectable(singleton=True)
    class Single:
        pass

    @injectable(singleton=False)
    class Consumable:
        pass

    assert isinstance(world.get(Single), Single)
    assert world.get(Single) is world.get(Single)

    assert isinstance(world.get(Consumable), Consumable)
    assert world.get(Consumable) is not world.get(Consumable)


def test_scope() -> None:
    scope = world.scopes.new(name="dummy")

    @injectable(scope=scope)
    class Scoped:
        pass

    scoped = world.get(Scoped)
    assert isinstance(scoped, Scoped)
    assert world.get(Scoped) is scoped

    world.scopes.reset(scope)

    new_scoped = world.get(Scoped)
    assert isinstance(new_scoped, Scoped)
    assert new_scoped is not scoped


def test_default_wiring() -> None:
    @injectable
    class Dummy:
        pass

    @injectable
    class WithWiring:
        def __init__(self, x: Dummy = inject.me()) -> None:
            self.dummy = x

        def method(self, x: Dummy = inject.me()) -> Dummy:
            return x

        @inject
        def injected_method(self, x: Dummy = inject.get(Dummy)) -> Dummy:
            return x

    @injectable(wiring=None)
    class NoWiring:
        def __init__(self, x: Dummy = inject.me()) -> None:
            self.dummy = x

        def method(self, x: Dummy = inject.me()) -> Dummy:
            return x

        @inject
        def injected_method(self, x: Dummy = inject.get(Dummy)) -> Dummy:
            return x

    dummy = world.get(Dummy)
    ww: WithWiring = world.get(WithWiring)
    assert ww.dummy is dummy
    assert ww.method() is dummy
    assert ww.injected_method() is dummy

    nw: NoWiring = world.get(NoWiring)
    assert nw.dummy is not dummy
    assert nw.method() is not dummy
    assert nw.injected_method() is dummy


def test_no_wiring() -> None:
    @injectable
    class Dummy:
        pass

    @injectable(wiring=None)
    class MyService:
        def __init__(self, x: Dummy = inject.me()) -> None:
            self.dummy = x

        def method(self, x: Inject[Dummy]) -> Dummy:
            ...

    service: MyService = world.get(MyService)
    assert isinstance(service, MyService)
    assert not isinstance(service.dummy, Dummy)

    with pytest.raises(TypeError):
        service.method()  # type: ignore


def test_custom_wiring() -> None:
    @injectable
    class Dummy:
        pass

    @injectable(wiring=Wiring(dependencies={"x": Dummy}))
    class MyService:
        def __init__(self, x: Dummy) -> None:
            self.dummy = x

        def method(self, x: Dummy) -> Dummy:
            return x

    service: MyService = world.get(MyService)
    assert isinstance(service, MyService)
    assert service.method() is world.get(Dummy)  # type: ignore


@pytest.mark.parametrize("factory_method", ["static_method", "class_method"])
def test_factory(factory_method: str) -> None:
    sentinel = object()

    @injectable(factory_method=factory_method)
    class Dummy:
        def __init__(self, x: object):
            self.x = x

        @classmethod
        def class_method(cls) -> Dummy:
            return Dummy(sentinel)

        @staticmethod
        def static_method() -> Dummy:
            return Dummy(sentinel)

    dummy: Dummy = world.get(Dummy)
    assert isinstance(dummy, Dummy)
    assert dummy is world.get(Dummy)
    assert dummy.x is sentinel


@pytest.mark.parametrize(
    "arg", ["singleton", "scope", "wiring", "factory_method", "type_hints_locals"]
)
def test_invalid_arguments(arg: str) -> None:
    with pytest.raises(TypeError, match=".*" + arg + ".*"):

        @injectable(**{arg: object()})  # type: ignore
        class Dummy:
            ...


def test_invalid_class() -> None:
    with pytest.raises(TypeError, match="(?i).*class.*"):
        injectable(object())  # type: ignore

    with pytest.raises(TypeError, match="(?i).*class.*"):
        injectable()(object())  # type: ignore


def test_invalid_factory_method() -> None:
    with pytest.raises(AttributeError, match=".*build.*"):

        @injectable(factory_method="build")
        class Dummy:
            ...

    with pytest.raises(TypeError, match=".*factory_method.*"):

        @injectable(factory_method="build")
        class Dummy2:
            build = 1

    with pytest.raises(TypeError, match=".*factory_method.*"):

        @injectable(factory_method="build")
        class Dummy3:
            def build(self) -> None:
                ...


def test_forbid_inheriting_service_class() -> None:
    with pytest.raises(DuplicateDependencyError, match=".*Service.*"):

        @injectable
        class Dummy(Service):
            ...


def test_duplicate_declaration() -> None:
    with pytest.raises(DuplicateDependencyError, match=".*Dummy.*"):

        @injectable
        @injectable
        class Dummy:
            ...
