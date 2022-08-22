# pyright: reportUnusedFunction=false, reportUnusedClass=false
from __future__ import annotations

import functools
import re
import sys
from dataclasses import dataclass, field
from typing import Callable, cast, Dict, Iterator, List, Optional, Sequence, Tuple, Union

import pytest

from antidote import (
    app_catalog,
    CannotInferDependencyError,
    DependencyNotFoundError,
    DoubleInjectionError,
    inject,
    InjectMe,
    new_catalog,
    PublicCatalog,
    world,
)
from tests.utils import Obj

default = Obj()
dep_x = Obj()
dep_y = Obj()
dep_z = Obj()
x = Obj()
y = Obj()
z = Obj()


class A(Obj):
    ...


@pytest.fixture(autouse=True)
def setup_world() -> Iterator[None]:
    with world.test.empty() as overrides:
        overrides.update({A: A(), dep_x: x, dep_y: y, dep_z: z})
        yield


def test_no_dependencies() -> None:
    def f() -> None:
        ...

    async def g() -> None:
        ...

    assert inject(f) is f
    assert inject(g) is g


def test_args() -> None:
    # simple case
    def f(a: object = default, b: object = default) -> Tuple[object, object]:
        return a, b

    assert inject(args=[dep_x, dep_y])(f)() == (x, y)
    assert inject(args=[None, dep_y])(f)() == (default, y)
    assert inject(args=[dep_x])(f)() == (x, default)

    # has_self
    class H:
        @inject(args=[dep_x])
        def method(self, a: object = default) -> None:
            assert isinstance(self, H)
            assert a is x

        @inject(args=[dep_x])
        @classmethod
        def cls_method_after(cls, a: object = default) -> None:
            assert issubclass(cls, H)
            assert a is x

        @classmethod
        @inject(args=[dep_x])
        def cls_method_before(cls, a: object = default) -> None:
            assert issubclass(cls, H)
            assert a is x

        # before will not work as the function will be treated as a method, expecting a self
        # parameter.
        @inject(args=[dep_x])
        @staticmethod
        def static_method_after(a: object = default) -> None:
            assert a is x

    h = H()
    h.method()
    h.cls_method_before()
    h.cls_method_after()
    h.static_method_after()

    H.method(h)
    H.cls_method_before()
    H.cls_method_after()
    H.static_method_after()

    with pytest.raises(TypeError, match="too many positional arguments"):

        @inject(args=[dep_x])
        def ff() -> None:
            ...

    @inject(args=[dep_x])
    def f2(a: object) -> object:
        ...

    with world.test.empty(), pytest.raises(DependencyNotFoundError):
        f2()  # type: ignore


def test_kwargs() -> None:
    @inject(kwargs=dict(a=dep_x))
    def f(a: object) -> object:
        return a

    assert f() is x  # type: ignore
    with world.test.empty(), pytest.raises(DependencyNotFoundError):
        f()  # type: ignore

    with pytest.raises(TypeError, match="hello"):

        @inject(kwargs=dict(hello=dep_x))
        def g(a: object) -> object:
            ...

    with pytest.raises(TypeError, match="kwargs.*mapping"):
        inject(kwargs={object(): object()})  # type: ignore

    with pytest.raises(TypeError, match="kwargs.*mapping"):
        inject(kwargs=[])  # type: ignore


def test_invalid_args_type() -> None:
    with pytest.raises(TypeError, match="str"):
        inject(args="test")

    with pytest.raises(TypeError, match="function"):
        inject(object())  # type: ignore

    with pytest.raises(TypeError, match="(?i)class.*@wire"):
        inject(A)


def test_fallback() -> None:
    def f(a: object) -> object:
        return a

    injected_f = inject(fallback=dict(a=dep_x))(f)
    assert injected_f() is x  # type: ignore
    with world.test.empty(), pytest.raises(DependencyNotFoundError):
        injected_f()  # type: ignore

    # no injections
    assert inject(fallback=dict(hello=dep_x))(f) is f

    with pytest.raises(TypeError, match="fallback.*mapping"):
        inject(fallback={object(): object()})  # type: ignore

    with pytest.raises(TypeError, match="fallback.*mapping"):
        inject(fallback=[])  # type: ignore


def test_ignore_type_hints() -> None:
    if sys.version_info >= (3, 9):
        with pytest.raises(NameError, match=".*name 'Unknown' is not defined.*"):

            @inject
            def f(a: "Unknown", b: object) -> Tuple[object, object]:
                ...

    @inject(ignore_type_hints=True, kwargs=dict(b=dep_x))
    def g(a: "Unknown", b: object = object()) -> Tuple[object, object]:
        return a, b

    class Unknown:
        ...

    unknown = Unknown()
    assert g(unknown) == (unknown, x)

    with pytest.raises(TypeError, match="ignore_type_hints"):
        inject(ignore_type_hints=object())  # type: ignore


def test_ignore_defaults() -> None:
    def f(a: A = inject.me(), b: object = inject[dep_x]) -> Tuple[object, object]:
        return a, b

    assert inject(f)() == (world[A], x)

    a, b = inject(ignore_defaults=True)(f)()
    assert not isinstance(a, A)
    assert b is not x

    with pytest.raises(TypeError, match="ignore_defaults"):
        inject(ignore_defaults=object())  # type: ignore


def test_invalid_inject() -> None:
    with pytest.raises(TypeError):
        inject(object())  # type: ignore

    with pytest.raises(TypeError):
        inject()(object())  # type: ignore


def test_follow_wrapped() -> None:
    @inject(kwargs=dict(a=dep_x))
    def f(a: object = object()) -> object:
        return a

    assert f() is x

    @functools.wraps(f)
    def g() -> object:
        return f()

    with pytest.raises(DoubleInjectionError):
        inject(g)

    assert g() is x


@pytest.mark.parametrize(
    "type_hint",
    # builtins
    cast(List[object], [str, int, float, set, list, dict, complex, type, tuple, bytes, bytearray])
    # typing
    + [Optional[int], Sequence[int]],
)
def test_invalid_type_hints(type_hint: object) -> None:
    with world.test.empty() as overrides:
        overrides[type_hint] = object()

        with pytest.raises(CannotInferDependencyError, match=re.escape(repr(type_hint))):

            @inject
            def f(x: InjectMe[type_hint]) -> None:  # type: ignore
                ...

        with pytest.raises(CannotInferDependencyError, match=re.escape(repr(type_hint))):

            @inject
            def g(x: type_hint = inject.me()) -> None:  # type: ignore
                ...


def test_ignore_star_arguments() -> None:
    def f(*args: object, a: object = None) -> Tuple[Tuple[object, ...], object]:
        return args, a

    assert inject(kwargs={"a": dep_x})(f)(y) == ((y,), x)

    with pytest.raises(TypeError, match="args"):
        inject(kwargs=dict(args=dep_x))(f)


def test_injection_ordering() -> None:
    def f(
        a: InjectMe[Union[A, None]] = None,
        b: object = inject[dep_x],
        c: object = None,
    ) -> Tuple[object, object, object]:
        return a, b, c

    assert inject(f)() == (world[A], x, None)

    # kwargs overrides defaults & annotations
    xyz = dict(a=dep_x, b=dep_y, c=dep_z)
    yzx = dict(a=dep_y, b=dep_z, c=dep_x)

    assert inject(kwargs=xyz)(f)() == (x, y, z)
    assert inject(args=[dep_x, dep_y, dep_z])(f)() == (x, y, z)
    assert inject(f, kwargs=xyz)() == (x, y, z)

    # kwargs overrides fallback
    assert inject(kwargs=xyz, fallback=yzx)(f)() == (x, y, z)
    assert inject(args=[dep_x, dep_y, dep_z], fallback=yzx)(f)() == (x, y, z)
    assert inject(f, kwargs=xyz, fallback=yzx)() == (x, y, z)

    # annotations & default override fallback
    assert inject(f, fallback=yzx)() == (world[A], x, x)
    assert inject(f, ignore_defaults=True, fallback=yzx)() == (world[A], z, x)
    assert inject(f, ignore_type_hints=True, fallback=yzx)() == (y, x, x)


# https://github.com/Finistere/antidote/issues/56
def test_problematic_type_hints() -> None:
    @inject
    def static(actions: Union[str, List[str]]) -> None:
        ...


def test_inject_catalog(catalog: PublicCatalog) -> None:
    catalog2 = new_catalog(include=[])

    with pytest.raises(TypeError):
        inject(app_catalog=object())  # type: ignore

    with catalog.test.empty() as catalog_overrides, catalog2.test.empty() as catalog2_overrides, world.test.empty() as overrides:
        overrides[A] = A()
        catalog_overrides[A] = A()
        catalog2_overrides[A] = A()

        def f(a: A = inject.me()) -> A:
            return a

        f_unspecified = inject(f)
        f_app = inject(f, app_catalog=app_catalog)
        f_catalog = inject(f, app_catalog=catalog)

        # Use current catalog by default
        assert f_unspecified() is world[A]
        assert f_app() is world[A]
        # Force specific catalog
        assert f_catalog() is catalog[A]

        @inject
        def g_unspecified_unspecified(a: A = inject.me()) -> A:
            return f_unspecified()

        @inject
        def g_unspecified_none(a: A = inject.me()) -> A:
            return f_app()

        @inject
        def g_unspecified_catalog(a: A = inject.me()) -> A:
            return f_catalog()

        @inject(app_catalog=catalog2)
        def g_catalog2_unspecified(a: A = inject.me()) -> A:
            return f_unspecified()

        @inject(app_catalog=catalog2)
        def g_catalog2_none(a: A = inject.me()) -> A:
            return f_app()

        @inject(app_catalog=catalog2)
        def g_catalog2_catalog(a: A = inject.me()) -> A:
            return f_catalog()

        assert g_unspecified_unspecified() is world[A]
        assert g_unspecified_none() is world[A]
        assert g_unspecified_catalog() is catalog[A]
        assert g_catalog2_unspecified() is catalog2[A]
        assert g_catalog2_none() is catalog2[A]
        assert g_catalog2_catalog() is catalog[A]


def test_inject_rewire(catalog: PublicCatalog) -> None:
    catalog2 = new_catalog(include=[])

    def f(a: A = inject.me()) -> A:
        return a

    # Nothing should happen
    inject.rewire(f, app_catalog=catalog)

    with pytest.raises(TypeError, match="catalog"):
        inject.rewire(f, app_catalog=object())  # type: ignore

    with pytest.raises(TypeError, match="function"):
        inject.rewire(object(), app_catalog=catalog)  # type: ignore

    with catalog.test.empty() as catalog_overrides, catalog2.test.empty() as catalog2_overrides, world.test.empty() as overrides:
        overrides[A] = A()
        catalog_overrides[A] = A()
        catalog2_overrides[A] = A()

        f_unspecified = inject(f)
        f_app = inject(f, app_catalog=app_catalog)
        f_catalog = inject(f, app_catalog=catalog)

        class Dummy:
            @inject
            @staticmethod
            def sm(a: A = inject.me()) -> A:
                return a

            @inject
            @classmethod
            def cm(cls, a: A = inject.me()) -> A:
                return a

            @inject
            def m(cls, a: A = inject.me()) -> A:
                return a

        inject.rewire(f_unspecified, app_catalog=catalog2)
        inject.rewire(f_app, app_catalog=catalog2)
        inject.rewire(f_catalog, app_catalog=catalog2)
        inject.rewire(Dummy.__dict__["sm"], app_catalog=catalog2)
        inject.rewire(Dummy.__dict__["cm"], app_catalog=catalog2)
        inject.rewire(Dummy.__dict__["m"], app_catalog=catalog2)

        assert isinstance(Dummy.__dict__["sm"], staticmethod)
        assert isinstance(Dummy.__dict__["cm"], classmethod)

        assert f_unspecified() is catalog2[A]
        assert f_app() is world[A]
        assert f_catalog() is catalog[A]
        assert Dummy.sm() is catalog2[A]
        assert Dummy.cm() is catalog2[A]
        assert Dummy().m() is catalog2[A]

        inject.rewire(f_unspecified, app_catalog=app_catalog)
        inject.rewire(f_app, app_catalog=app_catalog)
        inject.rewire(f_catalog, app_catalog=app_catalog)
        inject.rewire(Dummy.__dict__["sm"], app_catalog=app_catalog)  # pyright: ignore
        inject.rewire(Dummy.__dict__["cm"], app_catalog=app_catalog)  # pyright: ignore
        inject.rewire(Dummy.__dict__["m"], app_catalog=app_catalog)

        assert f_unspecified() is world[A]
        assert f_app() is world[A]
        assert f_catalog() is catalog[A]
        assert Dummy.sm() is world[A]
        assert Dummy.cm() is world[A]
        assert Dummy().m() is world[A]

        @inject(app_catalog=catalog2)
        def contextualized(func: Callable[[], A], a: A = inject.me()) -> A:
            return func()

        assert contextualized(f_unspecified) is catalog2[A]
        assert contextualized(f_app) is catalog2[A]
        assert contextualized(f_catalog) is catalog[A]
        assert contextualized(Dummy.sm) is catalog2[A]
        assert contextualized(Dummy.cm) is catalog2[A]
        assert contextualized(Dummy().m) is catalog2[A]


def test_star_args() -> None:
    with world.test.empty() as overrides:
        overrides[x] = x

        @inject(kwargs=dict(a=x), ignore_type_hints=True)
        def f1(
            *args: object, a: object = None, **kwargs: object
        ) -> tuple[tuple[object, ...], object, dict[str, object]]:
            return args, a, kwargs

        assert f1() == ((), x, {})
        assert f1(1, 2, 3) == ((1, 2, 3), x, {})
        assert f1(b=2) == ((), x, dict(b=2))
        assert f1(1, b=2) == ((1,), x, dict(b=2))
        assert f1(a=3) == ((), 3, {})

        @inject(kwargs=dict(a=x), ignore_type_hints=True)
        def f2(
            a: object = None, *args: object, **kwargs: object
        ) -> tuple[tuple[object, ...], object, dict[str, object]]:
            return args, a, kwargs

        assert f2() == ((), x, {})
        assert f2(1, 2, 3) == ((2, 3), 1, {})
        assert f2(b=2) == ((), x, dict(b=2))
        assert f2(1, 2, b=2) == ((2,), 1, dict(b=2))
        assert f2(a=3) == ((), 3, {})


def test_post_wraps() -> None:
    with world.test.empty() as overrides:
        overrides[x] = x
        overrides[y] = y

        def f1(a: object) -> object:
            ...

        @functools.wraps(f1)
        @inject
        def f2(b: object = inject[x]) -> object:
            return b

        assert f2() is x

        @inject
        def g1(a: object = inject[y]) -> object:
            ...

        @functools.wraps(g1)
        @inject
        def g2(b: object = inject[x]) -> object:
            return b

        assert g2() is x


def test_method() -> None:
    @dataclass
    class Conf:
        data: Dict[str, object] = field(default_factory=dict)

        @inject.method
        def method(self) -> object:
            return self

        @inject.method
        def get(self, key: str) -> object:
            return self.data[key]

    with pytest.raises(DependencyNotFoundError, match="Conf"):
        Conf.method()

    with pytest.raises(DependencyNotFoundError, match="Conf"):
        Conf.get("test")

    with world.test.empty() as overrides:
        conf = Conf({"k": x})
        overrides[Conf] = conf

        assert Conf.method() is conf
        assert conf.method() is conf
        assert Conf.get("k") is x
        assert conf.get("k") is x

        conf2 = Conf({"k": y})
        assert conf2.method() is conf2
        assert conf2.get(key="k") is y

    with pytest.raises(TypeError, match="inject.method"):

        @inject.method
        def f(self: object) -> None:
            ...

    class Dummy:
        with pytest.raises(TypeError, match="inject.method"):

            @inject.method
            @classmethod
            def klass(cls) -> object:
                ...

        with pytest.raises(TypeError, match="inject.method"):

            @inject.method  # type: ignore
            @staticmethod
            def static() -> object:
                ...

        with pytest.raises(TypeError, match="inject.method"):

            @staticmethod  # type: ignore
            @inject.method  # pyright: ignore
            def no_args() -> object:
                ...
