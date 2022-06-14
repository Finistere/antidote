# pyright: reportUnusedFunction=false, reportUnusedClass=false
from __future__ import annotations

import pytest

from antidote import config
from antidote.core import app_catalog, CannotInferDependencyError, inject, wire, Wiring, world


def test_locals() -> None:
    class Dummy:
        pass

    with world.test.empty() as overrides:
        overrides[Dummy] = Dummy()

        @inject
        def f(x: Dummy = inject.me()) -> Dummy:
            return x

        assert f() is world[Dummy]


def test_local_class() -> None:
    class Dummy:
        pass

    with world.test.empty() as overrides:
        overrides[Dummy] = Dummy()

        class Service:
            @inject
            def method(self, x: Dummy = inject.me()) -> Dummy:
                return x

        assert Service().method() is world[Dummy]

        @wire
        class Service2:
            def method(self, x: Dummy = inject.me()) -> Dummy:
                return x

        assert Service2().method() is world[Dummy]


def test_forward_ref() -> None:
    def f(a: Dummy = inject.me()) -> object:
        return a

    class Service:
        def f(self, a: Dummy = inject.me()) -> object:
            return a

    class Dummy:
        ...

    with world.test.empty() as overrides:
        overrides[Dummy] = Dummy()

        wire(Service, type_hints_locals=dict(Dummy=Dummy))
        injected_f = inject(f, type_hints_locals=dict(Dummy=Dummy))

        assert injected_f() is world[Dummy]
        assert Service().f() is world[Dummy]


def test_local_nested_class() -> None:
    class Dummy:
        pass

    with world.test.empty() as overrides:
        overrides[Dummy] = Dummy()

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

        assert Service1.Service2.Service3().method() is world[Dummy]
        assert Service1.Service2.Service3b().method() is world[Dummy]


def test_invalid_locals() -> None:
    with pytest.raises(TypeError, match="type_hints_locals"):
        inject(type_hints_locals=object())  # type: ignore

    with pytest.raises(TypeError, match="type_hints_locals"):
        wire(type_hints_locals=object())  # type: ignore

    class Dummy:
        pass

    with pytest.raises(TypeError, match="type_hints_locals"):
        Wiring().wire(klass=Dummy, catalog=app_catalog, type_hints_locals=object())  # type: ignore


def test_explicit_locals() -> None:
    class Dummy:
        pass

    class AlternateDummy:
        pass

    with world.test.empty() as overrides:
        overrides[AlternateDummy] = AlternateDummy()

        @inject(type_hints_locals={"Dummy": AlternateDummy})
        def f(x: Dummy = inject.me()) -> Dummy:
            return x

        assert f() is world[AlternateDummy]  # type: ignore

        @wire(type_hints_locals={"Dummy": AlternateDummy})
        class Service:
            def method(self, x: Dummy = inject.me()) -> Dummy:
                return x

        assert Service().method() is world[AlternateDummy]  # type: ignore


def test_no_locals() -> None:
    class Dummy:
        pass

    with world.test.empty() as overrides:
        overrides[Dummy] = Dummy()

        with pytest.raises(NameError, match="Dummy"):

            @inject(type_hints_locals=None)
            def f(x: Dummy = inject.me()) -> Dummy:
                ...

        with pytest.raises(NameError, match="Dummy"):

            @inject(type_hints_locals={})
            def g(x: Dummy = inject.me()) -> Dummy:
                ...

        with pytest.raises(NameError, match="Dummy"):

            @wire(type_hints_locals=None)
            class F:
                def method(self, x: Dummy = inject.me()) -> Dummy:
                    ...

        with pytest.raises(NameError, match="Dummy"):

            @wire(type_hints_locals={})
            class G:
                def method(self, x: Dummy = inject.me()) -> Dummy:
                    ...


def test_no_type_hints() -> None:
    class Dummy:
        pass

    with world.test.empty() as overrides:
        overrides[Dummy] = Dummy()

        with pytest.raises(CannotInferDependencyError, match=r"inject\.me"):

            @inject(ignore_type_hints=True)
            def f(x: Dummy = inject.me()) -> Dummy:
                ...

        with pytest.raises(CannotInferDependencyError, match=r"inject\.me"):

            @wire(ignore_type_hints=True)
            class F:
                def method(self, x: Dummy = inject.me()) -> Dummy:
                    ...

        @inject(ignore_type_hints=True)
        def g(x: Dummy = inject[Dummy]) -> Dummy:
            return x

        # Sanity check
        assert g() is world[Dummy]


def test_config_not_activated() -> None:
    config.auto_detect_type_hints_locals = False
    try:

        class Dummy:
            pass

        with world.test.empty() as overrides:
            overrides[Dummy] = Dummy()

            with pytest.raises(NameError, match="Dummy"):

                @inject
                def f(x: Dummy = inject.me()) -> Dummy:
                    ...

            with pytest.raises(NameError, match="Dummy"):

                @wire
                class Service:
                    def method(self, x: Dummy = inject.me()) -> Dummy:
                        ...

    finally:
        config.auto_detect_type_hints_locals = True
