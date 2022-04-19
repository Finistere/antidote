from __future__ import annotations

from typing import Iterator

import pytest

from antidote import config, inject, wire, world


@pytest.fixture(autouse=True)
def setup_world() -> Iterator[None]:
    with world.test.empty():
        yield


def test_locals():
    class Dummy:
        pass

    dummy = Dummy()
    world.test.singleton(Dummy, dummy)

    @inject
    def f(x: Dummy = inject.me()) -> Dummy:
        return x

    assert f() is dummy


def test_local_class():
    class Dummy:
        pass

    dummy = Dummy()
    world.test.singleton(Dummy, dummy)

    class Service:
        @inject
        def method(self, x: Dummy = inject.me()) -> Dummy:
            return x

    assert Service().method() is dummy

    @wire
    class Service2:
        def method(self, x: Dummy = inject.me()) -> Dummy:
            return x

    assert Service2().method() is dummy


def test_local_nested_class():
    class Dummy:
        pass

    dummy = Dummy()
    world.test.singleton(Dummy, dummy)

    class Service1:
        class Service2:
            class Service3:
                @inject
                def method(self, x: Dummy = inject.me()) -> Dummy:
                    return x

            @wire
            class Service3b:
                def method(self, x: Dummy = inject.me()) -> Dummy:
                    return x

    assert Service1.Service2.Service3().method() is dummy
    assert Service1.Service2.Service3b().method() is dummy


def test_invalid_locals():
    with pytest.raises(TypeError, match="(?i).*type_hints_locals.*"):
        inject(type_hints_locals=object())  # type: ignore

    with pytest.raises(TypeError, match="(?i).*type_hints_locals.*"):
        wire(type_hints_locals=object())  # type: ignore


def test_explicit_locals():
    class Dummy:
        pass

    class AlternateDummy:
        pass

    alternate_dummy = AlternateDummy()
    world.test.singleton(AlternateDummy, alternate_dummy)

    @inject(type_hints_locals={'Dummy': AlternateDummy})
    def f(x: Dummy = inject.me()) -> Dummy:
        return x

    assert f() is alternate_dummy

    @wire(type_hints_locals={'Dummy': AlternateDummy})
    class Service:
        def method(self, x: Dummy = inject.me()) -> Dummy:
            return x

    assert Service().method() is alternate_dummy


def test_no_locals():
    class Dummy:
        pass

    dummy = Dummy()
    world.test.singleton(Dummy, dummy)

    with pytest.raises(NameError, match="(?i).*Dummy.*"):
        @inject(type_hints_locals=None)
        def f(x: Dummy = inject.me()) -> Dummy:
            return x

    with pytest.raises(NameError, match="(?i).*Dummy.*"):
        @inject(type_hints_locals={})
        def g(x: Dummy = inject.me()) -> Dummy:
            return x

    with pytest.raises(NameError, match="(?i).*Dummy.*"):
        @wire(type_hints_locals=None)
        class F:
            def method(self, x: Dummy = inject.me()) -> Dummy:
                return x

    with pytest.raises(NameError, match="(?i).*Dummy.*"):
        @wire(type_hints_locals={})
        class G:
            def method(self, x: Dummy = inject.me()) -> Dummy:
                return x


def test_no_type_hints():
    class Dummy:
        pass

    dummy = Dummy()
    world.test.singleton(Dummy, dummy)

    with pytest.raises(TypeError, match=".*@inject.me.*"):
        @inject(ignore_type_hints=True)
        def f(x: Dummy = inject.me()) -> Dummy:
            return x

    with pytest.raises(TypeError, match=".*@inject.me.*"):
        @wire(ignore_type_hints=True)
        class F:
            def method(self, x: Dummy = inject.me()) -> Dummy:
                return x

    with pytest.raises(TypeError, match=".*type_hints_locals.*"):
        inject(type_hints_locals={}, ignore_type_hints=True)

    with pytest.raises(TypeError, match=".*type_hints_locals.*"):
        wire(type_hints_locals={}, ignore_type_hints=True)

    @inject(ignore_type_hints=True)
    def g(x: Dummy = inject.get(Dummy)) -> Dummy:
        return x

    # Sanity check
    assert g() is world.get(Dummy)


def test_config_not_activated():
    config.auto_detect_type_hints_locals = False
    try:
        class Dummy:
            pass

        dummy = Dummy()
        world.test.singleton(Dummy, dummy)

        with pytest.raises(NameError, match=".*Dummy.*"):
            @inject
            def f(x: Dummy = inject.me()) -> Dummy:
                return x

        with pytest.raises(NameError, match=".*Dummy.*"):
            @wire
            class Service:
                def method(self, x: Dummy = inject.me()) -> Dummy:
                    return x

    finally:
        config.auto_detect_type_hints_locals = True
