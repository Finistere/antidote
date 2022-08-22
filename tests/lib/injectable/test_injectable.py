# pyright: reportUnusedClass=false
from __future__ import annotations

import pytest

from antidote import (
    antidote_lib_injectable,
    DuplicateDependencyError,
    inject,
    injectable,
    InjectMe,
    PublicCatalog,
    Wiring,
    world,
)


@pytest.fixture(autouse=True)
def setup_world() -> None:
    world.include(antidote_lib_injectable)


def test_simple() -> None:
    @injectable
    class Dummy:
        pass

    dummy = world[Dummy]
    assert isinstance(dummy, Dummy)
    # Singleton by default
    assert world[Dummy] is dummy

    @inject
    def f(x: Dummy = inject.me()) -> Dummy:
        return x

    assert f() is dummy

    @inject
    def f2(x: Dummy = inject[Dummy]) -> Dummy:
        return x

    assert f2() is dummy


def test_singleton() -> None:
    @injectable(lifetime="singleton")
    class Single:
        pass

    @injectable(lifetime="transient")
    class Consumable:
        pass

    assert isinstance(world[Single], Single)
    assert world[Single] is world[Single]

    assert isinstance(world[Consumable], Consumable)
    assert world[Consumable] is not world[Consumable]


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
        def injected_method(self, x: Dummy = inject[Dummy]) -> Dummy:
            return x

    @injectable(wiring=None)
    class NoWiring:
        def __init__(self, x: Dummy = inject.me()) -> None:
            self.dummy = x

        def method(self, x: Dummy = inject.me()) -> Dummy:
            return x

        @inject
        def injected_method(self, x: Dummy = inject[Dummy]) -> Dummy:
            return x

    dummy = world[Dummy]
    ww: WithWiring = world[WithWiring]
    assert ww.dummy is dummy
    assert ww.method() is dummy
    assert ww.injected_method() is dummy

    nw: NoWiring = world[NoWiring]
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

        def method(self, x: InjectMe[Dummy]) -> Dummy:
            ...

    service: MyService = world[MyService]
    assert isinstance(service, MyService)
    assert not isinstance(service.dummy, Dummy)

    with pytest.raises(TypeError):
        service.method()  # pyright: ignore


def test_custom_wiring() -> None:
    @injectable
    class Dummy:
        pass

    @injectable(wiring=Wiring(fallback={"x": Dummy}))
    class MyService:
        def __init__(self, x: Dummy) -> None:
            self.dummy = x

        def method(self, x: Dummy) -> Dummy:
            return x

    service: MyService = world[MyService]
    assert isinstance(service, MyService)
    assert service.method() is world[Dummy]  # type: ignore


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

    dummy: Dummy = world[Dummy]
    assert isinstance(dummy, Dummy)
    assert dummy is world[Dummy]
    assert dummy.x is sentinel


@pytest.mark.parametrize("arg", ["lifetime", "wiring", "factory_method", "type_hints_locals"])
def test_invalid_arguments(arg: str) -> None:
    with pytest.raises(TypeError, match=".*" + arg + ".*"):
        injectable(**{arg: object()})  # type: ignore


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


def test_duplicate_declaration() -> None:
    with pytest.raises(DuplicateDependencyError, match=".*Dummy.*"):

        @injectable
        @injectable
        class Dummy:
            ...


def test_catalog(catalog: PublicCatalog) -> None:
    catalog.include(antidote_lib_injectable)

    @injectable(catalog=catalog)
    class Dummy:
        ...

    assert Dummy not in world
    assert Dummy in catalog

    with pytest.raises(TypeError, match="catalog"):
        injectable(catalog=object())  # type: ignore


def test_private_accessible(catalog: PublicCatalog) -> None:
    catalog.include(antidote_lib_injectable)

    @injectable(catalog=catalog.private)
    class Private:
        ...

    @injectable(catalog=catalog)
    class Dummy:
        def __init__(self, private: Private = inject.me()) -> None:
            self.private = private

    @injectable(catalog=catalog)
    class Dummy2:
        @inject
        def __init__(self, private: Private = inject.me()) -> None:
            self.private = private

    assert catalog[Dummy].private is catalog.private[Private]
    assert catalog[Dummy2].private is catalog.private[Private]
