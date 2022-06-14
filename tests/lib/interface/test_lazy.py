# pyright: reportUnusedFunction=false
from __future__ import annotations

from typing import Sequence

import pytest

from antidote import (
    DependencyNotFoundError,
    DuplicateDependencyError,
    implements,
    inject,
    injectable,
    interface,
    is_lazy,
    lazy,
    new_catalog,
    overridable,
    world,
)
from antidote._internal import short_id
from antidote.lib.interface import antidote_interface
from tests.lib.interface.common import _, weighted
from tests.utils import Box, expected_debug


@pytest.fixture(autouse=True)
def setup_world() -> None:
    world.include(antidote_interface)


def test_interface_lazy() -> None:
    @interface.lazy
    def double_me(x: int) -> Box[int]:
        ...

    with pytest.raises(TypeError, match="@implements"):
        implements(double_me)  # type: ignore

    @implements.lazy(double_me)
    def double_me_impl(x: int) -> Box[int]:
        return Box(x * 2)

    assert world[double_me(7)] == Box(14)
    assert world[double_me(7)] is not world[double_me(7)]
    assert world[double_me.single()(7)] == Box(14)
    assert world[double_me.single()(7)] is not world[double_me.single()(7)]
    assert world[double_me.all()(7)] == [Box(14)]
    assert world[double_me.all()(7)] is not world[double_me.all()(7)]

    assert is_lazy(double_me_impl)
    assert double_me_impl not in world
    assert world.private[double_me_impl(6)] == Box(12)
    assert double_me_impl.__wrapped__(6) == Box(12)

    assert str(world.id) in repr(double_me)
    assert repr(double_me.__wrapped__) in repr(double_me)

    @inject
    def f(x: Box[int] = inject[double_me(9)]) -> Box[int]:
        return x

    @inject
    def f2(x: Box[int] = inject[double_me.single()(9)]) -> Box[int]:
        return x

    @inject
    def f3(x: Sequence[Box[int]] = inject[double_me.all()(9)]) -> Sequence[Box[int]]:
        return x

    assert f() == Box(18)
    assert f2() == Box(18)
    assert f3() == [Box(18)]

    name = "test_interface_lazy.<locals>.double_me"
    assert name in repr(double_me(7))
    assert name in repr(double_me.single()(7))
    assert name in repr(double_me.all()(7))

    @_(implements.lazy(double_me).when(weighted(1)))
    @lazy(lifetime="singleton")
    def double_me_lazy_impl(x: int) -> Box[int]:
        return Box(x * 3)

    assert is_lazy(double_me_lazy_impl)
    assert double_me_lazy_impl.__wrapped__(9) == Box(27)
    result = world[double_me_lazy_impl(7)]
    assert result == Box(21)
    assert world[double_me_lazy_impl(7)] is result

    assert world[double_me(7)] is result
    assert world[double_me.single()(7)] is result
    assert world[double_me.all()(7)] == [result, Box(14)]
    assert any(e is result for e in world[double_me.all()(7)])

    with pytest.raises(TypeError, match="function"):
        interface.lazy(object())  # type: ignore

    with pytest.raises(TypeError, match="function"):
        implements.lazy(double_me)(object())  # type: ignore

    with pytest.raises(TypeError, match="function"):
        implements.lazy(double_me).when(weighted(12))(object())  # type: ignore


def test_overridable_lazy() -> None:
    @overridable.lazy
    def double_me(x: int) -> Box[int]:
        return Box(x * 2)

    assert double_me.__wrapped__(6) == Box(12)
    assert world[double_me(7)] == Box(14)
    assert world[double_me(7)] is not world[double_me(7)]

    @inject
    def f(x: Box[int] = inject[double_me(9)]) -> Box[int]:
        return x

    assert f() == Box(18)

    @implements.lazy(double_me)
    def double_me_impl(x: int) -> Box[int]:
        return Box(x * 4)

    assert world[double_me(7)] == Box(28)
    assert world[double_me(7)] is not world[double_me(7)]

    @overridable.lazy
    @lazy(lifetime="singleton")
    def box_me(x: int) -> Box[int]:
        return Box(x * 2)

    result = world[box_me(7)]
    assert result == Box(14)
    assert world[box_me(7)] is result

    with pytest.raises(TypeError, match="function"):
        overridable.lazy(object())  # type: ignore


def test_lazy_predicates() -> None:
    @interface.lazy
    def double_me(x: int) -> int:
        ...

    @_(implements.lazy(double_me).when(qualified_by="a"))
    def fa(x: int) -> int:
        return x * 2

    @_(implements.lazy(double_me).when(qualified_by="b"))
    def fb(x: int) -> int:
        return x * 3

    assert world.private[fa(13)] == 26
    assert world.private[fb(13)] == 39
    assert world[double_me.single(qualified_by="a")(7)] == 14
    assert world[double_me.single(qualified_by="b")(7)] == 21


def test_lazy_default() -> None:
    @interface.lazy
    def double_me(x: int) -> Box[int]:
        ...

    @_(implements.lazy(double_me).by_default)
    def default(x: int) -> Box[int]:
        return Box(x * 2)

    assert world[double_me(3)] == Box(6)
    assert world[double_me(3)] is not world[double_me(3)]

    assert is_lazy(default)
    assert default not in world
    assert world.private[default(6)] == Box(12)
    assert default.__wrapped__(6) == Box(12)

    @implements.lazy(double_me)
    def impl(x: int) -> Box[int]:
        return Box(x * 3)

    assert world[double_me(3)] == Box(9)
    assert world[double_me(3)] is not world[double_me(3)]

    @interface.lazy
    def double_me2(x: int) -> Box[int]:
        ...

    @_(implements.lazy(double_me2).by_default)
    @lazy(lifetime="singleton")
    def default2(x: int) -> Box[int]:
        return Box(x * 2)

    assert is_lazy(default2)
    assert default2.__wrapped__(9) == Box(18)
    result = world[default2(3)]
    assert result == Box(6)
    assert world[default2(3)] is result
    assert world[double_me2(3)] is result

    with pytest.raises(TypeError, match="function"):
        implements.lazy(double_me).by_default(object())  # type: ignore


def test_lazy_overriding() -> None:
    @interface.lazy
    def double_me(x: int) -> Box[int]:
        ...

    @_(implements.lazy(double_me).by_default)
    def default(x: int) -> Box[int]:
        return Box(x * 2)

    assert world[double_me(2)] == Box(4)

    @_(implements.lazy(double_me).overriding(default))
    def default_override(x: int) -> Box[int]:
        return Box(x * 3)

    assert world[double_me(3)] == Box(9)
    assert world[double_me(3)] is not world[double_me(3)]

    assert is_lazy(default_override)
    assert default_override not in world
    assert world.private[default_override(6)] == Box(18)
    assert default_override.__wrapped__(6) == Box(18)

    @implements.lazy(double_me)
    def impl(x: int) -> Box[int]:
        return Box(x * 4)

    assert world[double_me(3)] == Box(12)

    @_(implements.lazy(double_me).overriding(impl))
    def impl_override(x: int) -> Box[int]:
        return Box(x * 5)

    assert world[double_me(3)] == Box(15)
    assert world[double_me(3)] is not world[double_me(3)]

    assert is_lazy(impl_override)
    assert impl_override not in world
    assert world.private[impl_override(6)] == Box(30)
    assert impl_override.__wrapped__(6) == Box(30)

    with pytest.raises(TypeError, match="function"):
        implements.lazy(double_me).overriding(object())  # type: ignore

    with pytest.raises(TypeError, match="function"):
        implements.lazy(double_me).overriding(impl_override)(object())  # type: ignore


def test_lazy_overriding_lazy() -> None:
    @interface.lazy
    def double_me(x: int) -> Box[int]:
        ...

    @_(implements.lazy(double_me).by_default)
    @lazy  # ensures overriding works on lazy
    def default(x: int) -> Box[int]:
        return Box(x * 2)

    assert world[double_me(2)] == Box(4)

    @_(implements.lazy(double_me).overriding(default))
    @lazy(lifetime="singleton")
    def default_override(x: int) -> Box[int]:
        return Box(x * 3)

    assert is_lazy(default_override)
    assert default_override.__wrapped__(9) == Box(27)
    out = world[default_override(3)]
    assert out == Box(9)
    assert world[default_override(3)] is out
    assert world[double_me(3)] is out

    @implements.lazy(double_me)
    @lazy
    def impl(x: int) -> Box[int]:
        return Box(x * 4)

    assert world[double_me(3)] == Box(12)

    @_(implements.lazy(double_me).overriding(impl))
    @lazy(lifetime="singleton")
    def impl_override(x: int) -> Box[int]:
        return Box(x * 5)

    assert is_lazy(impl_override)
    assert impl_override.__wrapped__(9) == Box(45)
    out = world[impl_override(3)]
    assert out == Box(15)
    assert world[impl_override(3)] is out
    assert world[double_me(3)] is out

    with pytest.raises(TypeError, match="function"):
        implements.lazy(double_me).overriding(object())  # type: ignore


def test_injection_and_type_hints() -> None:
    @injectable(catalog=world.private)
    class Dep:
        pass

    with pytest.raises(NameError, match="Dep"):

        @overridable.lazy(type_hints_locals=None)
        def error(dep: Dep = inject.me()) -> object:
            ...

    injected = world.private[Dep]
    not_injected = inject.me()

    @overridable.lazy
    def dummy(dep: Dep = inject.me()) -> object:
        return dep

    @overridable.lazy
    @inject(dict(dep=Dep))
    def dummy_custom(dep: object = None) -> object:
        return dep

    @overridable.lazy(inject=None)
    def dummy_none(dep: Dep = inject.me()) -> object:
        return dep

    @overridable.lazy
    @lazy(inject=None)
    def dummy_lazy_none(dep: Dep = inject.me()) -> object:
        return dep

    assert world[dummy()] == injected
    assert world[dummy_custom()] == injected
    assert world[dummy_none()] == not_injected
    assert world[dummy_lazy_none()] == not_injected
    assert dummy.__wrapped__() == not_injected
    assert dummy_custom.__wrapped__() is None
    assert dummy_none.__wrapped__() == not_injected
    assert dummy_lazy_none.__wrapped__() == not_injected

    @implements.lazy(dummy)
    def dummy_impl(dep: Dep = inject.me()) -> object:
        return "impl", dep

    @implements.lazy(dummy_custom)
    @inject(dict(dep=Dep))
    def dummy_custom_impl(dep: object = None) -> object:
        return "impl", dep

    @implements.lazy(dummy_none, inject=None)
    def dummy_none_impl(dep: Dep = inject.me()) -> object:
        return "impl", dep

    @implements.lazy(dummy_lazy_none)
    @lazy(inject=None)
    def dummy_lazy_none_impl(dep: Dep = inject.me()) -> object:
        return "impl", dep

    assert world[dummy()] == ("impl", injected)
    assert world[dummy_custom()] == ("impl", injected)
    assert world[dummy_none()] == ("impl", not_injected)
    assert world[dummy_lazy_none()] == ("impl", not_injected)
    assert world.private[dummy_impl()] == ("impl", injected)
    assert world.private[dummy_custom_impl()] == ("impl", injected)
    assert world.private[dummy_none_impl()] == ("impl", not_injected)
    assert world[dummy_lazy_none_impl()] == ("impl", not_injected)
    assert dummy_impl.__wrapped__() == ("impl", not_injected)
    assert dummy_custom_impl.__wrapped__() == ("impl", None)
    assert dummy_none_impl.__wrapped__() == ("impl", not_injected)
    assert dummy_lazy_none_impl.__wrapped__() == ("impl", not_injected)

    @_(implements.lazy(dummy).overriding(dummy_impl))
    def dummy_override(dep: Dep = inject.me()) -> object:
        return "overriding", dep

    @_(implements.lazy(dummy_custom).overriding(dummy_custom_impl))
    @inject(dict(dep=Dep))
    def dummy_custom_override(dep: object = None) -> object:
        return "overriding", dep

    @_(implements.lazy(dummy_none, inject=None).overriding(dummy_none_impl))
    def dummy_none_override(dep: Dep = inject.me()) -> object:
        return "overriding", dep

    @_(implements.lazy(dummy_lazy_none).overriding(dummy_lazy_none_impl))
    @lazy(inject=None)
    def dummy_lazy_none_override(dep: Dep = inject.me()) -> object:
        return "overriding", dep

    assert world[dummy()] == ("overriding", injected)
    assert world[dummy_custom()] == ("overriding", injected)
    assert world[dummy_none()] == ("overriding", not_injected)
    assert world[dummy_lazy_none()] == ("overriding", not_injected)
    assert world.private[dummy_override()] == ("overriding", injected)
    assert world.private[dummy_custom_override()] == ("overriding", injected)
    assert world.private[dummy_none_override()] == ("overriding", not_injected)
    assert world[dummy_lazy_none_override()] == ("overriding", not_injected)
    assert dummy_override.__wrapped__() == ("overriding", not_injected)
    assert dummy_custom_override.__wrapped__() == ("overriding", None)
    assert dummy_none_override.__wrapped__() == ("overriding", not_injected)
    assert dummy_lazy_none_override.__wrapped__() == ("overriding", not_injected)

    @_(implements.lazy(dummy).when(weighted(12)))
    def dummy_when(dep: Dep = inject.me()) -> object:
        return "when", dep

    @_(implements.lazy(dummy_custom).when(weighted(12)))
    @inject(dict(dep=Dep))
    def dummy_custom_when(dep: object = None) -> object:
        return "when", dep

    @_(implements.lazy(dummy_none, inject=None).when(weighted(12)))
    def dummy_none_when(dep: Dep = inject.me()) -> object:
        return "when", dep

    @_(implements.lazy(dummy_lazy_none).when(weighted(12)))
    @lazy(inject=None)
    def dummy_lazy_none_when(dep: Dep = inject.me()) -> object:
        return "when", dep

    assert world[dummy()] == ("when", injected)
    assert world[dummy_custom()] == ("when", injected)
    assert world[dummy_none()] == ("when", not_injected)
    assert world[dummy_lazy_none()] == ("when", not_injected)
    assert world.private[dummy_when()] == ("when", injected)
    assert world.private[dummy_custom_when()] == ("when", injected)
    assert world.private[dummy_none_when()] == ("when", not_injected)
    assert world[dummy_lazy_none_when()] == ("when", not_injected)
    assert dummy_when.__wrapped__() == ("when", not_injected)
    assert dummy_custom_when.__wrapped__() == ("when", None)
    assert dummy_none_when.__wrapped__() == ("when", not_injected)
    assert dummy_lazy_none_when.__wrapped__() == ("when", not_injected)


def test_implementation_arguments_validation() -> None:
    @interface.lazy
    def info(xxx: int, yyy: str) -> str:
        ...

    with pytest.raises(TypeError, match="arguments.*yyy"):

        @implements.lazy(info)  # type: ignore
        def info_impl_x(xxx: int) -> str:
            ...

    with pytest.raises(TypeError, match="arguments.*xxx"):

        @implements.lazy(info)  # type: ignore
        def info_impl_y(yyy: str) -> str:
            ...

    @implements.lazy(info)
    def info_impl_xy(xxx: int, yyy: str) -> str:
        ...

    @implements.lazy(info)
    def info_impl_xyz(xxx: int, yyy: str, zzz: float = 0.1) -> str:
        ...


def test_catalog() -> None:
    catalog = new_catalog(include=[antidote_interface])

    @interface.lazy(catalog=catalog)
    def dummy() -> str:
        ...

    assert dummy() in catalog
    assert dummy() not in world

    @_(implements.lazy(dummy).by_default)
    def dummy_default() -> str:
        return "default"

    assert catalog[dummy()] == "default"
    assert dummy() not in world

    @_(implements.lazy(dummy).overriding(dummy_default))
    def dummy_default_override() -> str:
        return "default_override"

    assert catalog[dummy()] == "default_override"
    assert dummy() not in world

    @implements.lazy(dummy)
    def dummy_imp() -> str:
        return "impl"

    assert catalog[dummy()] == "impl"
    assert dummy() not in world

    @_(implements.lazy(dummy).overriding(dummy_imp))
    def dummy_impl_override() -> str:
        return "impl_override"

    assert catalog[dummy()] == "impl_override"
    assert dummy() not in world

    @_(implements.lazy(dummy).when(qualified_by="a"))
    def dummy_a() -> str:
        return "a"

    assert catalog[dummy.single(qualified_by="a")()] == "a"
    assert dummy() not in world

    @overridable.lazy(catalog=catalog)
    def dummy2() -> str:
        return "dummy2"

    assert dummy2() in catalog
    assert dummy2() not in world
    assert catalog[dummy2()] == "dummy2"


def test_test_env() -> None:
    @interface.lazy
    def dummy() -> Box[str]:
        ...

    @_(implements.lazy(dummy).by_default)
    @lazy(lifetime="singleton")
    def dummy_default() -> Box[str]:
        return Box("default")

    original_default = world[dummy()]

    with world.test.empty():
        assert dummy() not in world

    assert world[dummy()] is original_default

    with world.test.new():
        with pytest.raises(DependencyNotFoundError):
            __: object = world[dummy()]

    assert world[dummy()] is original_default

    with world.test.clone():
        assert dummy() in world
        result = world[dummy()]
        assert result == original_default
        assert result is not original_default

        @_(implements.lazy(dummy).overriding(dummy_default))
        def dummy_imp2() -> Box[str]:
            return Box("super")

        assert world[dummy()] == Box("super")

    assert world[dummy()] is original_default

    with world.test.copy():
        assert dummy() in world
        result = world[dummy()]
        assert result is original_default

        @_(implements.lazy(dummy).overriding(dummy_default))
        def dummy_imp3() -> Box[str]:
            return Box("super")

        assert world[dummy()] == Box("super")

    assert world[dummy()] is original_default

    @implements.lazy(dummy)
    @lazy(lifetime="singleton")
    def dummy_imp() -> Box[str]:
        return Box("impl")

    original = world[dummy()]

    with world.test.empty():
        assert dummy() not in world

    assert world[dummy()] is original

    with world.test.new():
        with pytest.raises(DependencyNotFoundError):
            __ = world[dummy()]  # noqa: F841

    assert world[dummy()] is original

    with world.test.clone():
        assert dummy() in world
        result = world[dummy()]
        assert result == original
        assert result is not original

        @_(implements.lazy(dummy).when(weighted(10)))
        def dummy_imp4() -> Box[str]:
            return Box("super")

        assert world[dummy()] == Box("super")

    assert world[dummy()] is original

    with world.test.copy():
        assert dummy() in world
        result = world[dummy()]
        assert result is original

        @_(implements.lazy(dummy).when(weighted(10)))
        def dummy_imp5() -> Box[str]:
            return Box("super")

        assert world[dummy()] == Box("super")

    assert world[dummy()] is original


def test_debug() -> None:
    namespace = f"tests.lib.interface.test_lazy.{test_debug.__name__}.<locals>"

    @interface.lazy
    def dummy(a: int = 0, *, b: str = "") -> str:
        ...

    @_(implements.lazy(dummy).by_default)
    def dummy_default(a: int = 0, *, b: str = "") -> str:
        ...

    assert world.debug(dummy.single()()) == expected_debug(
        f"""
    ∅ <lazy-single> {namespace}.dummy()
    └── ∅ <single> {namespace}.dummy
        └── 🟉 [Default] <const> <lazy function {namespace}.dummy_default #{short_id(dummy_default)}>
    """
    )

    assert world.debug(dummy.all()()) == expected_debug(
        f"""
    ∅ <lazy-all> {namespace}.dummy()
    └── ∅ <all> {namespace}.dummy
        └── 🟉 [Default] <const> <lazy function {namespace}.dummy_default #{short_id(dummy_default)}>
    """
    )

    @implements.lazy(dummy)
    def dummy_impl(a: int = 0, *, b: str = "") -> str:
        ...

    assert world.debug(dummy()) == expected_debug(
        f"""
    ∅ <lazy-single> {namespace}.dummy()
    └── ∅ <single> {namespace}.dummy
        └── 🟉 <const> <lazy function {namespace}.dummy_impl #{short_id(dummy_impl)}>
    """
    )

    assert world.debug(dummy.single()()) == expected_debug(
        f"""
    ∅ <lazy-single> {namespace}.dummy()
    └── ∅ <single> {namespace}.dummy
        └── 🟉 <const> <lazy function {namespace}.dummy_impl #{short_id(dummy_impl)}>
    """
    )

    assert world.debug(dummy.all()()) == expected_debug(
        f"""
    ∅ <lazy-all> {namespace}.dummy()
    └── ∅ <all> {namespace}.dummy
        └── 🟉 <const> <lazy function {namespace}.dummy_impl #{short_id(dummy_impl)}>
    """
    )

    assert world.debug(dummy(12, b="hello")) == expected_debug(
        f"""
    ∅ <lazy-single> {namespace}.dummy(12, b='hello')
    └── ∅ <single> {namespace}.dummy
        └── 🟉 <const> <lazy function {namespace}.dummy_impl #{short_id(dummy_impl)}>
    """
    )

    assert world.debug(dummy.single()(12, b="hello")) == expected_debug(
        f"""
    ∅ <lazy-single> {namespace}.dummy(12, b='hello')
    └── ∅ <single> {namespace}.dummy
        └── 🟉 <const> <lazy function {namespace}.dummy_impl #{short_id(dummy_impl)}>
    """
    )

    assert world.debug(dummy.all()(12, b="hello")) == expected_debug(
        f"""
    ∅ <lazy-all> {namespace}.dummy(12, b='hello')
    └── ∅ <all> {namespace}.dummy
        └── 🟉 <const> <lazy function {namespace}.dummy_impl #{short_id(dummy_impl)}>
    """
    )

    @_(implements.lazy(dummy).when(qualified_by="a"))
    def dummy_a(a: int = 0, *, b: str = "") -> str:
        ...

    assert world.debug(dummy()) == expected_debug(
        f"""
    ∅ <lazy-single> {namespace}.dummy()
    └── ∅ <single> {namespace}.dummy
        ├── 🟉 [NeutralWeight] <const> <lazy function {namespace}.dummy_a #{short_id(dummy_a)}>
        └── 🟉 [NeutralWeight] <const> <lazy function {namespace}.dummy_impl #{short_id(dummy_impl)}>
    """
    )

    assert world.debug(dummy.single(qualified_by="a")()) == expected_debug(
        f"""
    ∅ <lazy-single> {namespace}.dummy()
    └── ∅ <single> {namespace}.dummy // qualified_by=['a']
        └── 🟉 <const> <lazy function {namespace}.dummy_a #{short_id(dummy_a)}>
    """
    )

    assert world.debug(dummy.single(qualified_by="a")(12, b="hello")) == expected_debug(
        f"""
    ∅ <lazy-single> {namespace}.dummy(12, b='hello')
    └── ∅ <single> {namespace}.dummy // qualified_by=['a']
        └── 🟉 <const> <lazy function {namespace}.dummy_a #{short_id(dummy_a)}>
    """
    )

    assert world.debug(dummy.single(qualified_by_one_of=["a"])()) == expected_debug(
        f"""
    ∅ <lazy-single> {namespace}.dummy()
    └── ∅ <single> {namespace}.dummy // qualified_by_one_of=['a']
        └── 🟉 <const> <lazy function {namespace}.dummy_a #{short_id(dummy_a)}>
    """
    )


def test_duplicate_interface() -> None:
    def dummy() -> None:
        ...

    interface.lazy(dummy)
    with pytest.raises(DuplicateDependencyError, match="dummy"):
        interface.lazy(dummy)

    with pytest.raises(DuplicateDependencyError, match="dummy"):
        overridable.lazy(dummy)

    with pytest.raises(DuplicateDependencyError, match="dummy"):
        overridable.lazy(lazy(dummy))
