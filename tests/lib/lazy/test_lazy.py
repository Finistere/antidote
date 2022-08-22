# pyright: reportUnusedClass=false, reportUnusedFunction=false
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Optional

import pytest

from antidote import (
    antidote_lib_injectable,
    antidote_lib_lazy,
    Dependency,
    DuplicateDependencyError,
    inject,
    injectable,
    lazy,
    LifeTime,
    new_catalog,
    ScopeGlobalVar,
    world,
)
from antidote._internal import debug_repr
from antidote.lib.lazy_ext import Lazy
from tests.utils import Box, expected_debug, Obj

w = Obj()
x = Obj()
y = Obj()
z = Obj()


@pytest.fixture(autouse=True)
def setup_tests() -> None:
    world.include(antidote_lib_lazy)


def test_function() -> None:
    @lazy
    def dummy() -> Box[str]:
        return Box("test")

    # The call is a dependency, not the lazy function itself
    assert dummy not in world
    dependency: Dependency[Box[str]] = dummy()
    assert dependency in world

    d: Box[str] = world[dependency]
    # Singleton by default
    assert d is world[dependency]
    assert d is world[dummy()]
    assert d == Box("test")

    @inject
    def f(a: Box[str] = inject[dependency]) -> Box[str]:
        return a

    assert isinstance(f(), Box)
    assert f() == Box("test")
    assert f() is f()

    assert dummy.__wrapped__() == Box("test")

    debug_name = f"tests.lib.lazy.test_lazy.{test_function.__name__}.<locals>.dummy"
    assert repr(dummy.__wrapped__) in repr(dummy)
    assert repr(dummy.__wrapped__) in repr(dummy())
    assert str(world.id) in repr(dummy)
    assert str(world.id) in repr(dummy())
    assert debug_name in world.debug(dummy())
    assert re.search("lazy function.*" + re.escape(debug_name), debug_repr(dummy))


def test_value() -> None:
    @lazy.value
    def dummy() -> Box[str]:
        return Box("test")

    # The call is a dependency, not the lazy function itself
    dependency: Dependency[Box[str]] = dummy
    assert dependency in world

    d: Box[str] = world[dependency]
    # Singleton by default
    assert d is world[dependency]
    assert d is world[dummy]
    assert d == Box("test")

    @inject
    def f(a: Box[str] = inject[dependency]) -> Box[str]:
        return a

    assert isinstance(f(), Box)
    assert f() == Box("test")
    assert f() is f()

    assert dummy.__wrapped__() == Box("test")

    debug_name = f"tests.lib.lazy.test_lazy.{test_value.__name__}.<locals>.dummy"
    assert repr(dummy.__wrapped__) in repr(dummy)
    assert str(world.id) in repr(dummy)
    assert debug_name in world.debug(dummy)
    assert re.search(f"lazy value.*{re.escape(debug_name)}", debug_repr(dummy))


def test_static_method() -> None:
    class Dummy:
        @staticmethod
        @lazy
        def before(key: str) -> Box[str]:
            return Box(key)

        @lazy
        @staticmethod
        def after(key: str) -> Box[str]:
            return Box(key)

    assert isinstance(Dummy.__dict__["before"], staticmethod)
    assert isinstance(Dummy.__dict__["after"], staticmethod)

    # The call is a dependency, not the lazy function itself
    assert Dummy not in world
    assert Dummy.before not in world
    assert Dummy.after not in world
    dependency_before: Dependency[Box[str]] = Dummy.before("b")
    dependency_after: Dependency[Box[str]] = Dummy.after("a")
    assert dependency_before in world
    assert dependency_after in world

    b: Box[str] = world[dependency_before]
    a: Box[str] = world[dependency_after]
    # Singleton by default
    assert b is world[dependency_before]
    assert b == Box("b")
    assert a is world[dependency_after]
    assert a == Box("a")

    @inject
    def f(
        b_: Box[str] = inject[dependency_before], a_: Box[str] = inject[dependency_after]
    ) -> object:
        return b_, a_

    assert f() == (b, a)

    assert Dummy.before.__wrapped__("key") == Box("key")
    assert Dummy.after.__wrapped__("key") == Box("key")

    namespace = f"tests.lib.lazy.test_lazy.{test_static_method.__name__}.<locals>"
    assert repr(Dummy.before.__wrapped__) in repr(Dummy.before)
    assert repr(Dummy.before.__wrapped__) in repr(dependency_before)
    assert str(world.id) in repr(Dummy.before)
    assert str(world.id) in repr(dependency_before)
    assert f"{namespace}.Dummy.before" in world.debug(dependency_before)

    assert repr(Dummy.after.__wrapped__) in repr(Dummy.after)
    assert repr(Dummy.after.__wrapped__) in repr(dependency_after)
    assert str(world.id) in repr(Dummy.after)
    assert str(world.id) in repr(dependency_after)
    assert f"{namespace}.Dummy.after" in world.debug(dependency_after)


def test_method() -> None:
    world.include(antidote_lib_injectable)

    @injectable
    @dataclass
    class Dummy:
        data: Dict[str, object] = field(default_factory=dict)

        @lazy.method
        def get(self, key: str) -> Box[object]:
            return Box(self.data.get(key))

    # The call is a dependency, not the lazy function itself
    assert Dummy.get not in world
    dependency: Dependency[Box[object]] = Dummy.get("key")
    assert dependency in world

    d: Box[object] = world[dependency]
    # Singleton by default
    assert d is world[dependency]
    assert d is world[Dummy.get("key")]
    assert d == Box(None)

    @inject
    def f(a: Box[object] = inject[dependency]) -> Box[object]:
        return a

    assert f() == Box(None)
    assert f() is f()

    assert Dummy.get.__wrapped__(Dummy({"key": x}), "key") == Box(x)
    assert "Dummy.get" in repr(Dummy.get)
    assert "Dummy.get" in repr(dependency)
    assert str(world.id) in repr(Dummy.get)
    assert str(world.id) in repr(dependency)
    namespace = f"tests.lib.lazy.test_lazy.{test_method.__name__}.<locals>"
    assert f"{namespace}.Dummy.get" in world.debug(Dummy.get("key"))
    assert re.search(f"lazy method.*{re.escape(f'{namespace}.Dummy.get')}", debug_repr(Dummy.get))


def test_property() -> None:
    world.include(antidote_lib_injectable)

    @injectable
    @dataclass
    class Dummy:
        data: Dict[str, object] = field(default_factory=dict)

        @lazy.property
        def key(self) -> Box[object]:
            return Box(self.data.get("key"))

    dependency: Dependency[Box[object]] = Dummy.key
    assert dependency in world

    d: Box[object] = world[dependency]
    # Singleton by default
    assert d is world[dependency]
    assert d is world[Dummy.key]
    assert d == Box(None)

    @inject
    def f(a: Box[object] = inject[dependency]) -> Box[object]:
        return a

    assert f() == Box(None)
    assert f() is f()

    assert Dummy.key.__wrapped__(Dummy({"key": x})) == Box(x)
    assert repr(Dummy.key.__wrapped__) in repr(Dummy.key)
    assert str(world.id) in repr(Dummy.key)
    namespace = f"tests.lib.lazy.test_lazy.{test_property.__name__}.<locals>"
    assert f"{namespace}.Dummy.key" in world.debug(Dummy.key)
    assert re.search(f"lazy property.*{re.escape(f'{namespace}.Dummy.key')}", debug_repr(Dummy.key))


def test_private_class_dependency() -> None:
    world.include(antidote_lib_injectable)

    @injectable(catalog=world.private)
    @dataclass
    class Dummy:
        data: Dict[str, object] = field(default_factory=lambda: {"key": object()})

        @lazy.method(lifetime="transient")
        def get(self, key: str) -> Box[object]:
            return Box(self.data.get(key))

        @lazy.property(lifetime="transient")
        def key(self) -> Box[object]:
            return Box(self.data.get("key"))

    assert Dummy not in world
    # Using the same object
    assert world[Dummy.get("key")] == world[Dummy.key]
    assert world[Dummy.key] == Box(world.private[Dummy].data["key"])

    world.private[Dummy].data["key"] = x
    assert world[Dummy.get("key")] == Box(x)
    assert world[Dummy.key] == Box(x)


@pytest.mark.parametrize(
    "func", [pytest.param(lazy, id="lazy"), lazy.value, lazy.method, lazy.property]
)
def test_invalid_lazy(func: Lazy) -> None:
    with pytest.raises(TypeError, match="catalog"):
        func(catalog=object())  # type: ignore

    with pytest.raises(TypeError, match="inject"):
        func(inject=object())  # type: ignore

    with pytest.raises(TypeError, match="type_hints_locals"):
        func(type_hints_locals=object())  # type: ignore

    with pytest.raises(TypeError, match="function"):
        func(object())  # type: ignore


def test_duplicate_lazy() -> None:
    with pytest.raises(DuplicateDependencyError, match="existing lazy"):

        @lazy
        @lazy
        def f1() -> int:
            ...

    with pytest.raises(DuplicateDependencyError, match="existing lazy"):

        @lazy.value  # type: ignore
        @lazy.value
        def f2() -> int:
            ...

    class Dummy:
        with pytest.raises(DuplicateDependencyError, match="existing lazy"):

            @lazy.method  # type: ignore
            @lazy.method
            def f3(self) -> int:
                ...

        with pytest.raises(DuplicateDependencyError, match="existing lazy"):

            @lazy.property  # type: ignore
            @lazy.property
            def f4(self) -> int:
                ...

        with pytest.raises(DuplicateDependencyError, match="existing lazy"):

            @lazy
            @lazy
            @staticmethod
            def f5() -> int:
                ...

        with pytest.raises(DuplicateDependencyError, match="existing lazy"):

            @lazy
            @staticmethod
            @lazy
            def f6() -> int:
                ...


def test_transient() -> None:
    world.include(antidote_lib_injectable)

    @lazy(lifetime="transient")
    def func() -> Box[str]:
        return Box("x")

    @lazy.value(lifetime="transient")
    def value() -> Box[str]:
        return Box("x")

    @injectable
    class Dummy:
        @lazy.method(lifetime="transient")
        def method(self) -> Box[str]:
            return Box("x")

        @lazy.property(lifetime="transient")
        def prop(self) -> Box[str]:
            return Box("x")

        @lazy(lifetime="transient")
        @staticmethod
        def static_before() -> Box[str]:
            return Box("x")

        @staticmethod
        @lazy(lifetime="transient")
        def static_after() -> Box[str]:
            return Box("x")

    f = world[func()]
    v = world[value]
    m = world[Dummy.method()]
    p = world[Dummy.prop]
    sb = world[Dummy.static_before()]
    sa = world[Dummy.static_after()]
    expected = Box("x")
    assert f == expected
    assert v == expected
    assert m == expected
    assert p == expected
    assert sb == expected
    assert sa == expected

    assert world[func()] == f
    assert world[value] == v
    assert world[Dummy.method()] == m
    assert world[Dummy.prop] == p
    assert world[Dummy.static_before()] == sb
    assert world[Dummy.static_after()] == sa

    assert world[func()] is not f
    assert world[value] is not v
    assert world[Dummy.method()] is not m
    assert world[Dummy.prop] is not p
    assert world[Dummy.static_before()] is not sb
    assert world[Dummy.static_after()] is not sa


@pytest.mark.parametrize("lifetime", [LifeTime.SINGLETON, LifeTime.TRANSIENT])
def test_arguments(lifetime: LifeTime) -> None:
    world.include(antidote_lib_injectable)

    @lazy(lifetime=lifetime)
    def func(first: str, *, second: str = "") -> Box[str]:
        return Box(f"{first}{second}")

    @injectable
    class Dummy:
        @lazy.method(lifetime=lifetime)
        def method(self, first: str, *, second: str = "") -> Box[str]:
            return Box(f"{first}{second}")

        @lazy(lifetime=lifetime)
        @staticmethod
        def static_before(first: str, *, second: str = "") -> Box[str]:
            return Box(f"{first}{second}")

        @staticmethod
        @lazy(lifetime=lifetime)
        def static_after(first: str, *, second: str = "") -> Box[str]:
            return Box(f"{first}{second}")

    # Single argument
    f = world[func("test")]
    m = world[Dummy.method("test")]
    sb = world[Dummy.static_before("test")]
    sa = world[Dummy.static_after("test")]
    assert f == Box("test")
    assert m == Box("test")
    assert sb == Box("test")
    assert sa == Box("test")

    singleton = lifetime is LifeTime.SINGLETON
    assert (f is world[func("test")]) == singleton
    assert (m is world[Dummy.method("test")]) == singleton
    assert (sb is world[Dummy.static_before("test")]) == singleton
    assert (sa is world[Dummy.static_after("test")]) == singleton

    # Complex arguments
    assert world[func("Hello", second="World")] == Box("HelloWorld")
    assert world[Dummy.method("Hello", second="World")] == Box("HelloWorld")
    assert world[Dummy.static_before("Hello", second="World")] == Box("HelloWorld")
    assert world[Dummy.static_after("Hello", second="World")] == Box("HelloWorld")

    if lifetime is LifeTime.SINGLETON:
        assert world[func("1", second="2")] is world[func(first="1", second="2")]
        assert world[func("1")] is world[func(first="1")]

        assert world[Dummy.method("1", second="2")] is world[Dummy.method(first="1", second="2")]
        assert world[Dummy.method("1")] is world[Dummy.method(first="1")]

        assert (
            world[Dummy.static_before("1", second="2")]
            is world[Dummy.static_before(first="1", second="2")]
        )
        assert world[Dummy.static_before("1")] is world[Dummy.static_before(first="1")]

        assert (
            world[Dummy.static_after("1", second="2")]
            is world[Dummy.static_after(first="1", second="2")]
        )
        assert world[Dummy.static_after("1")] is world[Dummy.static_after(first="1")]

    # Invalid keyword argument
    with pytest.raises(TypeError):
        func(unknown="")  # type: ignore

    with pytest.raises(TypeError):
        Dummy.method(unknown="")  # type: ignore

    with pytest.raises(TypeError):
        Dummy.static_before(unknown="")  # type: ignore

    with pytest.raises(TypeError):
        Dummy.static_after(unknown="")  # type: ignore

    # Invalid positional argument number
    with pytest.raises(TypeError):
        func("1", "2")  # type: ignore

    with pytest.raises(TypeError):
        Dummy.method("1", "2")  # type: ignore

    with pytest.raises(TypeError):
        Dummy.static_before("1", "2")  # type: ignore

    with pytest.raises(TypeError):
        Dummy.static_after("1", "2")  # type: ignore


@pytest.mark.parametrize("lifetime", [LifeTime.SINGLETON, LifeTime.TRANSIENT])
def test_unhashable_arguments(lifetime: LifeTime) -> None:
    world.include(antidote_lib_injectable)

    @lazy(lifetime=lifetime)
    def func(a: object) -> Box[object]:
        return Box(a)

    @injectable
    class Dummy:
        @lazy.method(lifetime=lifetime)
        def method(self, a: object) -> Box[object]:
            return Box(a)

        @lazy(lifetime=lifetime)
        @staticmethod
        def static_before(a: object) -> Box[object]:
            return Box(a)

        @staticmethod
        @lazy(lifetime=lifetime)
        def static_after(a: object) -> Box[object]:
            return Box(a)

    if lifetime is LifeTime.SINGLETON:
        with pytest.raises(TypeError, match="unhashable"):
            func({})

        with pytest.raises(TypeError, match="unhashable"):
            Dummy.method({})

        with pytest.raises(TypeError, match="unhashable"):
            Dummy.static_before({})

        with pytest.raises(TypeError, match="unhashable"):
            Dummy.static_after({})
    else:
        assert world[func({})] == Box({})
        assert world[Dummy.method({})] == Box({})
        assert world[Dummy.static_before({})] == Box({})
        assert world[Dummy.static_after({})] == Box({})


def test_injection_and_type_hints() -> None:
    world.include(antidote_lib_injectable)

    @injectable(catalog=world.private)
    class Dummy:
        pass

    with pytest.raises(NameError, match="Dummy"):

        @lazy(type_hints_locals=None)
        def error(dummy: Dummy = inject.me()) -> object:
            ...

    @lazy
    def func1(dummy: Dummy = inject.me()) -> Dummy:
        return dummy

    @lazy
    @inject(kwargs={"dummy": Dummy})
    def func2(dummy: object = None) -> object:
        return dummy

    @lazy(inject=None)
    def func3(dummy: Dummy = inject.me()) -> Dummy:
        return dummy

    @lazy.value
    def value1(dummy: Dummy = inject.me()) -> Dummy:
        return dummy

    @lazy.value
    @inject(kwargs={"dummy": Dummy})
    def value2(dummy: object = None) -> object:
        return dummy

    @lazy.value(inject=None)
    def value3(dummy: Dummy = inject.me()) -> Dummy:
        return dummy

    @injectable
    class Holder:
        @lazy.method
        def method1(self, dummy: Dummy = inject.me()) -> Dummy:
            return dummy

        @lazy.method
        @inject(kwargs={"dummy": Dummy})
        def method2(self, dummy: object = None) -> object:
            return dummy

        @lazy.method(inject=None)
        def method3(self, dummy: Dummy = inject.me()) -> Dummy:
            return dummy

        @lazy.property
        def prop1(self, dummy: Dummy = inject.me()) -> Dummy:
            return dummy

        @lazy.property
        @inject(kwargs={"dummy": Dummy})
        def prop2(self, dummy: object = None) -> object:
            return dummy

        @lazy.property(inject=None)
        def prop3(self, dummy: Dummy = inject.me()) -> Dummy:
            return dummy

        @lazy
        @staticmethod
        def static_before1(dummy: Dummy = inject.me()) -> Dummy:
            return dummy

        @lazy
        @staticmethod
        @inject(kwargs={"dummy": Dummy})
        def static_before2(dummy: object = None) -> object:
            return dummy

        @lazy(inject=None)
        @staticmethod
        def static_before3(dummy: Dummy = inject.me()) -> Dummy:
            return dummy

        @staticmethod
        @lazy
        def static_after1(dummy: Dummy = inject.me()) -> Dummy:
            return dummy

        @staticmethod
        @lazy
        @inject(kwargs={"dummy": Dummy})
        def static_after2(dummy: object = None) -> object:
            return dummy

        @staticmethod
        @lazy(inject=None)
        def static_after3(dummy: Dummy = inject.me()) -> Dummy:
            return dummy

    injected = world.private[Dummy]
    not_injected = inject.me()

    assert func1.__wrapped__() == not_injected
    assert value1.__wrapped__() == not_injected
    assert Holder.method1.__wrapped__(Holder()) == not_injected
    assert Holder.prop1.__wrapped__(Holder()) == not_injected
    assert Holder.static_before1.__wrapped__() == not_injected
    assert Holder.static_after1.__wrapped__() == not_injected

    assert world[func1()] == injected
    assert world[value1] == injected
    assert world[Holder.method1()] == injected
    assert world[Holder.prop1] == injected
    assert world[Holder.static_before1()] == injected
    assert world[Holder.static_after1()] == injected

    assert world[func2()] == injected
    assert world[value2] == injected
    assert world[Holder.method2()] == injected
    assert world[Holder.prop2] == injected
    assert world[Holder.static_before2()] == injected
    assert world[Holder.static_after2()] == injected

    assert world[func3()] == not_injected
    assert world[value3] == not_injected
    assert world[Holder.method3()] == not_injected
    assert world[Holder.prop3] == not_injected
    assert world[Holder.static_before3()] == not_injected
    assert world[Holder.static_after3()] == not_injected


def test_catalog() -> None:
    catalog = new_catalog(include=[antidote_lib_lazy, antidote_lib_injectable])

    @lazy(catalog=catalog)
    def func() -> Box[str]:
        ...

    @lazy.value(catalog=catalog)
    def value() -> Box[str]:
        ...

    @injectable(catalog=catalog.private)
    class Dummy:
        @lazy.method(catalog=catalog)
        def method(self) -> Box[str]:
            ...

        @lazy.property(catalog=catalog)
        def prop(self) -> Box[str]:
            ...

        @lazy(catalog=catalog)
        @staticmethod
        def static_before() -> Box[str]:
            ...

        @staticmethod
        @lazy(catalog=catalog)
        def static_after() -> Box[str]:
            ...

    assert func() in catalog
    assert value in catalog
    assert Dummy.method() in catalog
    assert Dummy.prop in catalog
    assert Dummy.static_before() in catalog
    assert Dummy.static_after() in catalog

    assert func() not in world
    assert value not in world
    assert Dummy.method() not in world
    assert Dummy.prop not in world
    assert Dummy.static_before() not in world
    assert Dummy.static_after() not in world


@pytest.mark.parametrize("lifetime", [LifeTime.SINGLETON, LifeTime.TRANSIENT])
def test_test_env(lifetime: LifeTime) -> None:
    world.include(antidote_lib_injectable)

    @lazy(lifetime=lifetime)
    def func() -> Box[str]:
        return Box("func")

    @lazy.value(lifetime=lifetime)
    def value() -> Box[str]:
        return Box("value")

    @injectable
    class Dummy:
        @lazy.method(lifetime=lifetime)
        def method(self) -> Box[str]:
            return Box("method")

        @lazy.property(lifetime=lifetime)
        def prop(self) -> Box[str]:
            return Box("prop")

        @lazy(lifetime=lifetime)
        @staticmethod
        def static_before() -> Box[str]:
            return Box("static_before")

        @staticmethod
        @lazy(lifetime=lifetime)
        def static_after() -> Box[str]:
            return Box("static_after")

    assert Dummy in world
    assert Dummy in world.private
    original_func = world[func()]
    original_value = world[value]
    original_method = world[Dummy.method()]
    original_prop = world[Dummy.prop]
    original_static_before = world[Dummy.static_before()]
    original_static_after = world[Dummy.static_after()]

    with world.test.empty():
        assert func() not in world
        assert value not in world
        assert Dummy.method() not in world
        assert Dummy.prop not in world
        assert Dummy.static_before() not in world
        assert Dummy.static_after() not in world

    with world.test.new():
        assert func() not in world
        assert value not in world
        assert Dummy.method() not in world
        assert Dummy.prop not in world
        assert Dummy.static_before() not in world
        assert Dummy.static_after() not in world

        @lazy.value
        def example() -> str:
            return "test"

        assert example in world
        assert world[example] == "test"

    with world.test.clone():
        assert func() in world
        assert value in world
        assert Dummy.method() in world
        assert Dummy.prop in world
        assert Dummy.static_before() in world
        assert Dummy.static_after() in world
        assert world[func()] == original_func
        assert world[func()] is not original_func
        assert world[value] == original_value
        assert world[value] is not original_value
        assert world[Dummy.method()] == original_method
        assert world[Dummy.method()] is not original_method
        assert world[Dummy.prop] == original_prop
        assert world[Dummy.prop] is not original_prop
        assert world[Dummy.static_before()] == original_static_before
        assert world[Dummy.static_before()] is not original_static_before
        assert world[Dummy.static_after()] == original_static_after
        assert world[Dummy.static_after()] is not original_static_after

    with world.test.copy():
        assert func() in world
        assert value in world
        assert Dummy.method() in world
        assert Dummy.prop in world
        assert Dummy.static_before() in world
        assert Dummy.static_after() in world
        if lifetime is LifeTime.TRANSIENT:
            assert world[func()] == original_func
            assert world[value] == original_value
            assert world[Dummy.method()] == original_method
            assert world[Dummy.prop] == original_prop
            assert world[Dummy.static_before()] == original_static_before
            assert world[Dummy.static_after()] == original_static_after
        else:
            assert world[func()] is original_func
            assert world[value] is original_value
            assert world[Dummy.method()] is original_method
            assert world[Dummy.prop] is original_prop
            assert world[Dummy.static_before()] is original_static_before
            assert world[Dummy.static_after()] is original_static_after


def test_classmethod() -> None:
    class Failure:
        with pytest.raises(TypeError, match="classmethod"):

            @lazy.method
            @classmethod
            def f1(cls) -> object:
                ...

        with pytest.raises(TypeError, match="classmethod"):

            @lazy
            @classmethod
            def f2(cls) -> object:
                ...

        with pytest.raises(TypeError, match="classmethod"):

            @lazy.property
            @classmethod
            def f3(cls) -> object:
                ...


def test_require_lazy_on_staticmethod() -> None:
    class Failure:
        with pytest.raises(TypeError, match="staticmethod"):

            @lazy.method  # type: ignore
            @staticmethod
            def f1() -> object:
                ...


def test_debug() -> None:
    world.include(antidote_lib_injectable)

    @lazy
    def func(a: str = "a") -> Box[str]:
        ...

    @lazy.value
    def value() -> Box[str]:
        ...

    @injectable
    class Dummy:
        @lazy.method
        def method(self, a: str = "a") -> Box[str]:
            ...

        @lazy.property
        def prop(self) -> Box[str]:
            ...

        @lazy
        @staticmethod
        def static_before(a: str = "a") -> Box[str]:
            ...

        @staticmethod
        @lazy
        def static_after(a: str = "a") -> Box[str]:
            ...

        CONST = method("test")

    namespace = "tests.lib.lazy.test_lazy.test_debug.<locals>"
    assert world.debug(Dummy.CONST) == expected_debug(
        f"""
    🟉 <lazy> {namespace}.Dummy.CONST // {namespace}.Dummy.method('test')
    └── 🟉 {namespace}.Dummy
    """
    )
    assert world.debug(func()) == expected_debug(
        f"""
    🟉 <lazy> {namespace}.func()
    """
    )
    assert world.debug(value) == expected_debug(
        f"""
    🟉 <lazy> {namespace}.value()
    """
    )
    assert world.debug(Dummy.method()) == expected_debug(
        f"""
    🟉 <lazy> {namespace}.Dummy.method()
    └── 🟉 {namespace}.Dummy
    """
    )
    assert world.debug(Dummy.prop) == expected_debug(
        f"""
    🟉 <lazy> {namespace}.Dummy.prop()
    └── 🟉 {namespace}.Dummy
    """
    )
    assert world.debug(Dummy.static_before()) == expected_debug(
        f"""
    🟉 <lazy> {namespace}.Dummy.static_before()
    """
    )
    assert world.debug(Dummy.static_after()) == expected_debug(
        f"""
    🟉 <lazy> {namespace}.Dummy.static_after()
    """
    )
    assert world.debug(func(a="1")) == expected_debug(
        f"""
    🟉 <lazy> {namespace}.func('1')
    """
    )
    assert world.debug(Dummy.method(a="1")) == expected_debug(
        f"""
    🟉 <lazy> {namespace}.Dummy.method('1')
    └── 🟉 {namespace}.Dummy
    """
    )
    assert world.debug(Dummy.static_before(a="1")) == expected_debug(
        f"""
    🟉 <lazy> {namespace}.Dummy.static_before('1')
    """
    )
    assert world.debug(Dummy.static_after(a="1")) == expected_debug(
        f"""
    🟉 <lazy> {namespace}.Dummy.static_after('1')
    """
    )

    @lazy
    def f(*, d: Optional[Box[str]] = inject[func()]) -> None:
        ...

    # should not fail
    assert "Unknown" in world.debug(x)
    assert world.debug(f()) == expected_debug(
        f"""
    🟉 <lazy> {namespace}.f()
    └── 🟉 <lazy> {namespace}.func()
    """
    )
    assert world.debug(f(d=None)) == expected_debug(
        f"""
    🟉 <lazy> {namespace}.f(d=None)
    └── 🟉 <lazy> {namespace}.func()
    """
    )


def test_scoped() -> None:
    world.include(antidote_lib_injectable)
    version = ScopeGlobalVar[int](default=0)

    @lazy(lifetime="scoped")
    def func(v: int = inject[version]) -> Box[int]:
        return Box(v)

    @lazy.value(lifetime="scoped")
    def value(v: int = inject[version]) -> Box[int]:
        return Box(v)

    @injectable
    class Dummy:
        @lazy.method(lifetime="scoped")
        def method(self, v: int = inject[version]) -> Box[int]:
            return Box(v)

        @lazy.property(lifetime="scoped")
        def prop(self, v: int = inject[version]) -> Box[int]:
            return Box(v)

        @lazy(lifetime="scoped")
        @staticmethod
        def static_before(v: int = inject[version]) -> Box[int]:
            return Box(v)

        @staticmethod
        @lazy(lifetime="scoped")
        def static_after(v: int = inject[version]) -> Box[int]:
            return Box(v)

    original_func = world[func()]
    original_value = world[value]
    original_method = world[Dummy.method()]
    original_prop = world[Dummy.prop]
    original_static_before = world[Dummy.static_before()]
    original_static_after = world[Dummy.static_after()]
    assert original_func == Box(0)
    assert original_value == Box(0)
    assert original_method == Box(0)
    assert original_prop == Box(0)
    assert original_static_before == Box(0)
    assert original_static_after == Box(0)
    # Same value returned
    assert world[func()] is original_func
    assert world[value] is original_value
    assert world[Dummy.method()] is original_method
    assert world[Dummy.prop] is original_prop
    assert world[Dummy.static_before()] is original_static_before
    assert world[Dummy.static_after()] is original_static_after

    version.set(12)

    original_func = world[func()]
    original_value = world[value]
    original_method = world[Dummy.method()]
    original_prop = world[Dummy.prop]
    original_static_before = world[Dummy.static_before()]
    original_static_after = world[Dummy.static_after()]
    assert original_func == Box(12)
    assert original_value == Box(12)
    assert original_method == Box(12)
    assert original_prop == Box(12)
    assert original_static_before == Box(12)
    assert original_static_after == Box(12)
    # Same value returned
    assert world[func()] is original_func
    assert world[value] is original_value
    assert world[Dummy.method()] is original_method
    assert world[Dummy.prop] is original_prop
    assert world[Dummy.static_before()] is original_static_before
    assert world[Dummy.static_after()] is original_static_after

    with world.test.empty():
        assert func() not in world
        assert value not in world
        assert Dummy.method() not in world
        assert Dummy.prop not in world
        assert Dummy.static_before() not in world
        assert Dummy.static_after() not in world

    with world.test.new():
        assert func() not in world
        assert value not in world
        assert Dummy.method() not in world
        assert Dummy.prop not in world
        assert Dummy.static_before() not in world
        assert Dummy.static_after() not in world

    with world.test.clone():
        assert func() in world
        assert value in world
        assert Dummy.method() in world
        assert Dummy.prop in world
        assert Dummy.static_before() in world
        assert Dummy.static_after() in world

        # Using the default value of the scope var
        assert world[func()] == Box(0)
        assert world[value] == Box(0)
        assert world[Dummy.method()] == Box(0)
        assert world[Dummy.prop] == Box(0)
        assert world[Dummy.static_before()] == Box(0)
        assert world[Dummy.static_after()] == Box(0)

        version.set(44)
        # value changed
        assert world[func()] == Box(44)
        assert world[value] == Box(44)
        assert world[Dummy.method()] == Box(44)
        assert world[Dummy.prop] == Box(44)
        assert world[Dummy.static_before()] == Box(44)
        assert world[Dummy.static_after()] == Box(44)
        # cached
        assert world[func()] is world[func()]
        assert world[value] is world[value]
        assert world[Dummy.method()] is world[Dummy.method()]
        assert world[Dummy.prop] is world[Dummy.prop]
        assert world[Dummy.static_before()] is world[Dummy.static_before()]
        assert world[Dummy.static_after()] is world[Dummy.static_after()]

    # originals weren't touched
    assert world[func()] is original_func
    assert world[value] is original_value
    assert world[Dummy.method()] is original_method
    assert world[Dummy.prop] is original_prop
    assert world[Dummy.static_before()] is original_static_before
    assert world[Dummy.static_after()] is original_static_after

    with world.test.copy():
        assert func() in world
        assert value in world
        assert Dummy.method() in world
        assert Dummy.prop in world
        assert Dummy.static_before() in world
        assert Dummy.static_after() in world
        assert world[func()] is original_func
        assert world[value] is original_value
        assert world[Dummy.method()] is original_method
        assert world[Dummy.prop] is original_prop
        assert world[Dummy.static_before()] is original_static_before
        assert world[Dummy.static_after()] is original_static_after

        version.set(44)
        # value changed
        assert world[func()] == Box(44)
        assert world[value] == Box(44)
        assert world[Dummy.method()] == Box(44)
        assert world[Dummy.prop] == Box(44)
        assert world[Dummy.static_before()] == Box(44)
        assert world[Dummy.static_after()] == Box(44)
        # cached
        assert world[func()] is world[func()]
        assert world[value] is world[value]
        assert world[Dummy.method()] is world[Dummy.method()]
        assert world[Dummy.prop] is world[Dummy.prop]
        assert world[Dummy.static_before()] is world[Dummy.static_before()]
        assert world[Dummy.static_after()] is world[Dummy.static_after()]

    # originals weren't touched
    assert world[func()] is original_func
    assert world[value] is original_value
    assert world[Dummy.method()] is original_method
    assert world[Dummy.prop] is original_prop
    assert world[Dummy.static_before()] is original_static_before
    assert world[Dummy.static_after()] is original_static_after


def test_inject_signature() -> None:
    world.include(antidote_lib_injectable)

    @injectable
    class Service:
        pass

    @lazy
    @inject(kwargs=dict(service=Service))
    def f(service: object) -> object:
        return service

    @injectable
    class Dummy:
        @lazy.method
        @inject(kwargs=dict(service=Service))
        def method(self, service: object) -> object:
            return service

    assert world[f()] is world[Service]  # type: ignore
    assert world[Dummy.method()] is world[Service]  # type: ignore
