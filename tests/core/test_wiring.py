# pyright: reportUnusedFunction=false, reportUnusedClass=false
from __future__ import annotations

from typing import Any, Callable, cast, ClassVar, Iterable, Iterator, Mapping, Tuple, TypeVar, Union

import pytest
from typing_extensions import Protocol

from antidote import (
    app_catalog,
    CannotInferDependencyError,
    DoubleInjectionError,
    inject,
    InjectMe,
    Methods,
    new_catalog,
    ReadOnlyCatalog,
    TypeHintsLocals,
    Wiring,
    world,
)
from tests.utils import Obj

C = TypeVar("C", bound=type)

dep_x = Obj()
x = Obj()
y = Obj()


class A(Obj):
    ...


class Wire(Protocol):
    def __call__(
        self,
        *,
        app_catalog: ReadOnlyCatalog | None = None,
        methods: Methods | Iterable[str] = Methods.ALL,
        fallback: Mapping[str, object] | None = None,
        raise_on_double_injection: bool = False,
        ignore_type_hints: bool = False,
        type_hints_locals: TypeHintsLocals = None,
    ) -> Callable[[C], C]:
        ...


@pytest.fixture(params=["Wiring", "wire"])
def wire_(request: Any) -> Wire:
    kind = request.param
    if kind == "Wiring":

        def wiring(**kwargs: Any) -> Any:
            type_hints_locals = kwargs.pop("type_hints_locals", None)
            app_catalog = kwargs.pop("app_catalog", None)
            wiring = Wiring(**kwargs)

            def decorator(cls: type) -> type:
                wiring.wire(
                    klass=cls,
                    type_hints_locals=type_hints_locals,
                    app_catalog=app_catalog,
                )
                return cls

            return decorator

        return cast(Wire, wiring)
    else:
        from antidote import wire

        return cast(Wire, wire)


@pytest.fixture(autouse=True)
def setup_world() -> Iterator[None]:
    with world.test.empty() as overrides:
        overrides.update({A: A(), dep_x: x})
        yield


async def test_all_methods(wire_: Wire) -> None:
    def func(self: object, a: object = None) -> object:
        return a

    class Dummy:
        def __init__(self, a: object = None) -> None:
            self.a = a

        def __call__(self, a: object = None) -> object:
            return a

        my_func = func

        def method(self, a: object = None) -> object:
            return a

        def _method(self, a: object = None) -> object:
            return a

        def __method(self, a: object = None) -> object:
            return a

        @classmethod
        def klass(cls, a: object = None) -> object:
            return a

        @staticmethod
        def static(a: object = None) -> object:
            return a

        async def async_method(self, a: object = None) -> object:
            return a

        @classmethod
        async def async_klass(cls, a: object = None) -> object:
            return a

        @staticmethod
        async def async_static(a: object = None) -> object:
            return a

        # Not injected
        def nothing(self) -> None:
            ...

        def __getitem__(self, item: A = inject.me()) -> object:
            return item

        class Nested:
            def method(self, a: object = None) -> object:
                return a

            def method2(self, a: A = inject.me()) -> object:
                return a

        attribute: ClassVar[int] = 42

    pre_dummy = Dummy()
    wire_(fallback=dict(a=dep_x))(Dummy)
    post_dummy = Dummy()

    assert pre_dummy.a is None
    assert post_dummy.a is x

    for dummy in [pre_dummy, post_dummy]:
        assert dummy() is x
        assert dummy.method() is x
        assert dummy.my_func() is x
        assert dummy._method() is x  # pyright: ignore[reportPrivateUsage]
        assert dummy._Dummy__method() is x  # type: ignore
        assert dummy.klass() is x
        assert dummy.static() is x
        assert (await dummy.async_method()) is x
        assert (await dummy.async_klass()) is x
        assert (await dummy.async_static()) is x

    assert Dummy.method(pre_dummy) is x
    assert Dummy.klass() is x
    assert Dummy.static() is x
    assert (await Dummy.async_method(pre_dummy)) is x
    assert (await Dummy.async_klass()) is x
    assert (await Dummy.async_static()) is x

    assert isinstance(Dummy.__dict__["klass"], classmethod)
    assert isinstance(Dummy.__dict__["static"], staticmethod)
    assert isinstance(Dummy.__dict__["async_klass"], classmethod)
    assert isinstance(Dummy.__dict__["async_static"], staticmethod)

    # Not injected
    nested = Dummy.Nested()
    assert nested.method() is None
    assert not isinstance(nested.method2(), A) and nested.method2() is not world[A]

    for dummy in [pre_dummy, post_dummy]:
        assert not isinstance(dummy.__getitem__(), A) and dummy.__getitem__() is not world[A]

    assert pre_dummy.attribute == 42
    assert post_dummy.attribute == 42
    assert Dummy.attribute == 42


def test_explicit_method_names(wire_: Wire) -> None:
    @wire_(methods=iter(["f1", "f3"]))
    class Dummy:
        def f1(self, a: A = inject.me()) -> A:
            return a

        def f2(self, a: A = inject.me()) -> A:
            return a

        def f3(self, a: A = inject.me()) -> A:
            return a

    assert Dummy().f1() is world[A]
    assert Dummy().f2() is not world[A]
    assert Dummy().f3() is world[A]

    with pytest.raises(TypeError, match="methods"):
        wire_(methods=object())  # type: ignore

    with pytest.raises(TypeError, match="methods"):
        wire_(methods=[object()])  # type: ignore

    with pytest.raises(AttributeError, match="unknown_method"):

        @wire_(methods=["unknown_method"])
        class Dummy2:
            pass

    with pytest.raises(TypeError, match="not_a_method"):

        @wire_(methods=["not_a_method"])
        class Dummy3:
            not_a_method = 1


def test_fallback(wire_: Wire) -> None:
    @wire_(fallback=dict(a=dep_x))
    class Dummy:
        def f1(self, a: A = inject.me()) -> A:
            return a

        def f2(self, a: InjectMe[Union[A, None]] = None) -> Union[A, None]:
            return a

        def f3(self, a: object = None) -> object:
            return a

    assert Dummy().f1() is world[A]
    assert Dummy().f2() is world[A]
    assert Dummy().f3() is x

    with pytest.raises(TypeError, match="fallback"):
        wire_(fallback=object())  # type: ignore

    with pytest.raises(TypeError, match="fallback"):
        wire_(fallback={object(): object()})  # type: ignore


def test_double_injection(wire_: Wire) -> None:
    @wire_()
    class Dummy:
        def f1(self, a: A = inject.me()) -> A:
            return a

        @inject(kwargs=dict(a=dep_x))
        def f2(self, a: A = inject.me()) -> A:
            return a

    assert Dummy().f1() is world[A]
    assert Dummy().f2() is x

    with pytest.raises(DoubleInjectionError, match="f2"):

        @wire_(raise_on_double_injection=True)
        class Dummy2:
            @inject(kwargs=dict(a=dep_x))
            def f2(self, a: A = inject.me()) -> A:
                ...

    with pytest.raises(TypeError, match="raise_on_double_injection"):
        wire_(raise_on_double_injection=object())  # type: ignore


def test_ignore_type_hints(wire_: Wire) -> None:
    @wire_(ignore_type_hints=True, fallback=dict(a=dep_x))
    class Dummy:
        def method(self, a: "Unknown | None" = None) -> object:
            return a

    class Unknown:
        pass

    assert Dummy().method() is x

    with pytest.raises(TypeError, match="ignore_type_hints"):
        wire_(ignore_type_hints=object())  # type: ignore


def test_class_in_locals_by_default(wire_: Wire) -> None:
    @wire_()
    class Dummy:
        def method(self, a: A = inject.me()) -> Tuple[Dummy, A]:
            return self, a

    dummy = Dummy()
    assert dummy.method() == (dummy, world[A])


def test_invalid_class(wire_: Wire) -> None:
    with pytest.raises(TypeError):
        wire_()(object())  # type: ignore


def test_wiring_copy() -> None:
    wiring = Wiring()
    assert wiring.copy() == wiring
    assert wiring.copy(methods=["test"]) == Wiring(methods=["test"])
    assert wiring.copy(fallback=dict(x=x)) == Wiring(fallback=dict(x=x))
    assert wiring.copy(raise_on_double_injection=True) == Wiring(raise_on_double_injection=True)
    assert wiring.copy(ignore_type_hints=True) == Wiring(ignore_type_hints=True)

    w2 = wiring.copy(
        methods=["test"], fallback=dict(x=x), raise_on_double_injection=True, ignore_type_hints=True
    )
    assert w2 == Wiring(
        methods=["test"], fallback=dict(x=x), raise_on_double_injection=True, ignore_type_hints=True
    )
    assert w2.copy() == w2

    with pytest.raises(TypeError, match="methods"):
        wiring.copy(methods=object())  # type: ignore

    with pytest.raises(TypeError, match="methods"):
        wiring.copy(methods=[object()])  # type: ignore

    with pytest.raises(TypeError, match="fallback"):
        wiring.copy(fallback=object())  # type: ignore

    with pytest.raises(TypeError, match="fallback"):
        wiring.copy(fallback={object(): object()})  # type: ignore

    with pytest.raises(TypeError, match="raise_on_double_injection"):
        wiring.copy(raise_on_double_injection=object())  # type: ignore

    with pytest.raises(TypeError, match="ignore_type_hints"):
        wiring.copy(ignore_type_hints=object())  # type: ignore


def test_wiring_wire_klass() -> None:
    with pytest.raises(TypeError, match="class"):
        Wiring().wire(klass=object(), app_catalog=world)  # type: ignore

    with pytest.raises(TypeError, match="catalog"):
        Wiring().wire(klass=A, app_catalog=object())  # type: ignore


@pytest.mark.usefixtures("clean_config")
def test_wiring_wire_class_in_locals() -> None:
    with world.test.empty() as overrides:

        class Dummy:
            def f(self, a: Dummy = inject.me()) -> Dummy:
                return a

        dummy = Dummy()
        overrides[Dummy] = dummy

        with pytest.raises(NameError, match="Dummy"):
            Wiring().wire(klass=Dummy, class_in_locals=False, app_catalog=app_catalog)

        with pytest.raises(CannotInferDependencyError):
            Wiring(ignore_type_hints=True).wire(klass=Dummy, app_catalog=app_catalog)

        with pytest.raises(ValueError, match="class_in_locals"):
            Wiring(ignore_type_hints=True).wire(
                klass=Dummy, class_in_locals=True, app_catalog=app_catalog
            )

        assert dummy.f() is not dummy
        assert not isinstance(dummy.f(), Dummy)

        Wiring().wire(klass=Dummy, class_in_locals=True, app_catalog=app_catalog)
        assert dummy.f() is dummy

    with world.test.empty() as overrides:

        class Local:
            pass

        class Dummy2:
            def f(self, a: Dummy2 = inject.me(), b: Local = inject.me()) -> Tuple[Dummy2, Local]:
                return a, b

        dummy2 = Dummy2()
        overrides[Dummy2] = dummy2
        overrides[Local] = Local()

        with pytest.raises(NameError, match="Local"):
            Wiring().wire(klass=Dummy2, app_catalog=app_catalog)

        Wiring().wire(klass=Dummy2, type_hints_locals=dict(Local=Local), app_catalog=app_catalog)
        assert dummy2.f() == (dummy2, world[Local])

    with pytest.raises(TypeError, match="class_in_locals"):
        Wiring().wire(klass=Local, class_in_locals=object(), app_catalog=app_catalog)  # type: ignore


def test_catalog(wire_: Wire) -> None:
    class Dummy:
        @inject(args=[x])
        def f(self, a: object = None) -> object:
            return a

    assert Dummy().f() is None

    catalog = new_catalog(include=[])
    with catalog.test.empty() as overrides:
        overrides[x] = x

        wire_(app_catalog=catalog)(Dummy)
        assert Dummy().f() is x

    assert Dummy().f() is None

    class Dummy2:
        @inject(args=[x])
        def f(self, a: object = None) -> object:
            return a

    with world.test.empty() as overrides:
        overrides[x] = y

        wire_(app_catalog=None)(Dummy2)
        assert Dummy2().f() is y
