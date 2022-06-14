# pyright: reportUnusedFunction=false
from __future__ import annotations

import inspect
from typing import Sequence

import pytest

from antidote import (
    DependencyNotFoundError,
    DuplicateDependencyError,
    implements,
    inject,
    injectable,
    interface,
    lazy,
    new_catalog,
    overridable,
    world,
)
from antidote.lib.interface import antidote_interface
from tests.lib.interface.common import _, weighted
from tests.utils import Box, expected_debug


@pytest.fixture(autouse=True)
def setup_world() -> None:
    world.include(antidote_interface)


def test_interface_function() -> None:
    @interface
    def double_me(x: int) -> object:
        ...

    with pytest.raises(TypeError, match="@implements.lazy"):
        implements.lazy(double_me)  # type: ignore

    @implements(double_me)
    def double_me_impl(x: int) -> object:
        return f"Hello {x}!"

    assert inspect.isfunction(double_me_impl)
    assert double_me_impl(12) == "Hello 12!"
    assert world[double_me] is double_me_impl  # type: ignore
    assert world[double_me.single()] is double_me_impl  # type: ignore
    assert world[double_me.all()] == [double_me_impl]

    assert str(world.id) in repr(double_me)
    assert repr(double_me.__wrapped__) in repr(double_me)

    @inject
    def f(x: object = inject[double_me]) -> object:
        return x

    @inject
    def f2(x: object = inject[double_me.single()]) -> object:
        return x

    @inject
    def f3(x: Sequence[object] = inject[double_me.all()]) -> Sequence[object]:
        return x

    assert f() is double_me_impl
    assert f2() is double_me_impl
    assert f3() == [double_me_impl]

    name = "test_interface_function.<locals>.double_me"
    assert name in repr(double_me)
    assert name in repr(double_me.single())
    assert name in repr(double_me.all())

    @_(implements(double_me).when(weighted(1)))
    def double_me_super(x: object) -> object:
        return "super", x

    assert inspect.isfunction(double_me_super)
    assert double_me_super(12) == ("super", 12)
    assert world[double_me] is double_me_super  # type: ignore
    assert world[double_me.single()] is double_me_super  # type: ignore
    assert world[double_me.all()] == [double_me_super, double_me_impl]

    with pytest.raises(TypeError, match="function"):
        interface(object())  # type: ignore

    with pytest.raises(TypeError, match="function"):
        implements(double_me)(object())  # type: ignore

    with pytest.raises(TypeError, match="function"):
        implements(double_me).when(weighted(12))(object())  # type: ignore


def test_overridable_function() -> None:
    @overridable
    def double_me(x: int) -> object:
        return "double_me", x

    assert double_me.__wrapped__(17) == ("double_me", 17)
    assert world[double_me] is double_me.__wrapped__

    @inject
    def f(x: object = inject[double_me]) -> object:
        return x

    assert f() is double_me.__wrapped__

    @implements(double_me)
    def double_me_impl(x: int) -> object:
        ...

    assert f() is double_me_impl
    assert world[double_me] is double_me_impl

    with pytest.raises(TypeError, match="function"):
        overridable(object())  # type: ignore


def test_function_predicates() -> None:
    @interface
    def double_me(x: int) -> int:
        ...

    @_(implements(double_me).when(qualified_by="a"))
    def fa(x: int) -> int:
        ...

    @_(implements(double_me).when(qualified_by="b"))
    def fb(x: int) -> int:
        ...

    assert world[double_me.single(qualified_by="a")] is fa
    assert world[double_me.single(qualified_by="b")] is fb


def test_function_default() -> None:
    @interface
    def double_me(x: int) -> object:
        ...

    @_(implements(double_me).by_default)
    def default(x: int) -> object:
        return Box(x * 2)

    assert inspect.isfunction(default)
    assert default(8) == Box(16)
    assert world[double_me] is default  # type: ignore

    @implements(double_me)
    def impl(x: int) -> object:
        ...

    assert world[double_me] is impl

    with pytest.raises(TypeError, match="function"):
        implements(double_me).by_default(object())  # type: ignore


def test_function_overriding() -> None:
    @interface
    def double_me(x: int) -> object:
        ...

    @_(implements(double_me).by_default)
    def default(x: int) -> object:
        ...

    assert world[double_me] is default

    @_(implements(double_me).overriding(default))
    def default_override(x: int) -> object:
        return Box(x * 3)

    assert inspect.isfunction(default_override)
    assert default_override(8) == Box(24)
    assert world[double_me] is default_override  # type: ignore

    @implements(double_me)
    def impl(x: int) -> object:
        ...

    assert world[double_me] is impl

    @_(implements(double_me).overriding(impl))
    def impl_override(x: int) -> object:
        return Box(x * 5)

    assert inspect.isfunction(impl_override)
    assert impl_override(8) == Box(40)
    assert world[double_me] is impl_override  # type: ignore

    with pytest.raises(TypeError, match="function"):
        implements(double_me).overriding(object())  # type: ignore

    with pytest.raises(TypeError, match="function"):
        implements(double_me).overriding(impl_override)(object())  # type: ignore


def test_injection_and_type_hints() -> None:
    @injectable(catalog=world.private)
    class Dummy:
        pass

    with pytest.raises(NameError, match="Dummy"):

        @overridable(type_hints_locals=None)
        def error(dummy: Dummy = inject.me()) -> object:
            ...

    injected = world.private[Dummy]
    not_injected = inject.me()

    @overridable
    def factor_me(dummy: Dummy = inject.me()) -> object:
        return dummy

    @overridable
    @inject(dict(dummy=Dummy))
    def factor_me_custom(dummy: object = None) -> object:
        return dummy

    @overridable(inject=None)
    def factor_me_none(dummy: Dummy = inject.me()) -> object:
        return dummy

    assert world[factor_me]() == injected
    assert world[factor_me_custom]() == injected
    assert world[factor_me_none]() == not_injected
    assert factor_me.__wrapped__() == not_injected
    assert factor_me_custom.__wrapped__() is None
    assert factor_me_none.__wrapped__() == not_injected

    @implements(factor_me)
    def factor_me_impl(dummy: Dummy = inject.me()) -> object:
        return "impl", dummy

    @implements(factor_me_custom)
    @inject(dict(dummy=Dummy))
    def factor_me_custom_impl(dummy: object = None) -> object:
        return "impl", dummy

    @implements(factor_me_none, inject=None)
    def factor_me_none_impl(dummy: Dummy = inject.me()) -> object:
        return "impl", dummy

    assert world[factor_me]() == ("impl", injected)
    assert world[factor_me_custom]() == ("impl", injected)
    assert world[factor_me_none]() == ("impl", not_injected)
    assert factor_me_impl() == ("impl", injected)
    assert factor_me_custom_impl() == ("impl", injected)
    assert factor_me_none_impl() == ("impl", not_injected)
    assert factor_me_impl.__wrapped__() == ("impl", not_injected)  # type: ignore
    assert factor_me_custom_impl.__wrapped__() == ("impl", None)  # type: ignore

    @_(implements(factor_me).overriding(factor_me_impl))
    def factor_me_override(dummy: Dummy = inject.me()) -> object:
        return "overriding", dummy

    @_(implements(factor_me_custom).overriding(factor_me_custom_impl))
    @inject(dict(dummy=Dummy))
    def factor_me_custom_override(dummy: object = None) -> object:
        return "overriding", dummy

    @_(implements(factor_me_none, inject=None).overriding(factor_me_none_impl))
    def factor_me_none_override(dummy: Dummy = inject.me()) -> object:
        return "overriding", dummy

    assert world[factor_me]() == ("overriding", injected)
    assert world[factor_me_custom]() == ("overriding", injected)
    assert world[factor_me_none]() == ("overriding", not_injected)
    assert factor_me_override() == ("overriding", injected)
    assert factor_me_custom_override() == ("overriding", injected)
    assert factor_me_none_override() == ("overriding", not_injected)
    assert factor_me_override.__wrapped__() == ("overriding", not_injected)  # type: ignore
    assert factor_me_custom_override.__wrapped__() == ("overriding", None)  # type: ignore

    @_(implements(factor_me).when(weighted(12)))
    def factor_me_when(dummy: Dummy = inject.me()) -> object:
        return "when", dummy

    @_(implements(factor_me_custom).when(weighted(12)))
    @inject(dict(dummy=Dummy))
    def factor_me_custom_when(dummy: object = None) -> object:
        return "when", dummy

    @_(implements(factor_me_none, inject=None).when(weighted(12)))
    def factor_me_none_when(dummy: Dummy = inject.me()) -> object:
        return "when", dummy

    assert world[factor_me]() == ("when", injected)
    assert world[factor_me_custom]() == ("when", injected)
    assert world[factor_me_none]() == ("when", not_injected)
    assert factor_me_when() == ("when", injected)
    assert factor_me_custom_when() == ("when", injected)
    assert factor_me_none_when() == ("when", not_injected)
    assert factor_me_when.__wrapped__() == ("when", not_injected)  # type: ignore
    assert factor_me_custom_when.__wrapped__() == ("when", None)  # type: ignore


def test_implementation_arguments_validation() -> None:
    @interface
    def dummy(first: int, second: str = "second") -> str:
        ...

    with pytest.raises(TypeError, match="arguments.*second"):

        @implements(dummy)  # type: ignore
        def dummy_impl_first(first: int) -> str:
            ...

    with pytest.raises(TypeError, match="arguments.*first"):

        @implements(dummy)  # type: ignore
        def dummy_impl_second(second: str = "second") -> str:
            ...

    with pytest.raises(TypeError, match="argument.*first.*at position 1"):

        @implements(dummy)  # type: ignore
        def dummy_impl_reversed(second: str = "second", first: str = "first") -> str:
            ...

    with pytest.raises(TypeError, match="default value.*second"):

        @implements(dummy)  # type: ignore
        def dummy_impl_no_default(first: str, second: str) -> str:
            ...

    # Should not fail
    @implements(dummy)
    def dummy_impl(first: int, second: str = "second") -> str:
        ...

    @implements(dummy)
    def dummy_impl_third(first: int, second: str = "second", third: float = 0.1) -> str:
        ...

    @interface
    def keywords(*, first: int, second: str) -> str:
        ...

    # Should not fail
    @implements(keywords)
    def keywords_impl(second: str, first: int) -> str:
        ...


def test_catalog() -> None:
    catalog = new_catalog(include=[antidote_interface])

    @interface(catalog=catalog)
    def dummy() -> str:
        ...

    assert dummy in catalog
    assert dummy not in world

    @_(implements(dummy).by_default)
    def dummy_default() -> str:
        ...

    assert catalog[dummy] is dummy_default
    assert dummy not in world

    @_(implements(dummy).overriding(dummy_default))
    def dummy_default_override() -> str:
        ...

    assert catalog[dummy] is dummy_default_override
    assert dummy not in world

    @implements(dummy)
    def dummy_impl() -> str:
        ...

    assert catalog[dummy] is dummy_impl
    assert dummy not in world

    @_(implements(dummy).overriding(dummy_impl))
    def dummy_impl_override() -> str:
        ...

    assert catalog[dummy] is dummy_impl_override
    assert dummy not in world

    @_(implements(dummy).when(qualified_by="a"))
    def dummy_a() -> str:
        ...

    assert catalog[dummy.single(qualified_by="a")] is dummy_a
    assert dummy not in world

    @overridable(catalog=catalog)
    def dummy2() -> str:
        ...

    assert dummy2 in catalog
    assert dummy2 not in world
    assert catalog[dummy2] is dummy2.__wrapped__


def test_test_env() -> None:
    @interface
    def dummy() -> Box[str]:
        ...

    @_(implements(dummy).by_default)
    def dummy_default() -> Box[str]:
        ...

    assert world[dummy] is dummy_default

    with world.test.empty():
        assert dummy not in world

    assert world[dummy] is dummy_default

    with world.test.new():
        # TODO: to fix?
        assert dummy not in world
        with pytest.raises(DependencyNotFoundError):
            __: object = world[dummy]

    assert world[dummy] is dummy_default

    with world.test.clone():
        assert dummy in world
        assert world[dummy] is dummy_default

        @_(implements(dummy).overriding(dummy_default))
        def dummy_imp2() -> Box[str]:
            ...

        assert world[dummy] is dummy_imp2

    assert world[dummy] is dummy_default

    with world.test.copy():
        assert dummy in world
        assert world[dummy] is dummy_default

        @_(implements(dummy).overriding(dummy_default))
        def dummy_imp2() -> Box[str]:
            ...

        assert world[dummy] is dummy_imp2

    assert world[dummy] is dummy_default

    @implements(dummy)
    def dummy_impl() -> Box[str]:
        ...

    assert world[dummy] is dummy_impl

    with world.test.empty():
        assert dummy not in world

    assert world[dummy] is dummy_impl

    with world.test.new():
        with pytest.raises(DependencyNotFoundError):
            __ = world[dummy]()  # noqa: F841

    assert world[dummy] is dummy_impl

    with world.test.clone():
        assert dummy in world
        assert world[dummy] is dummy_impl

        @_(implements(dummy).when(weighted(10)))
        def dummy_impl2() -> Box[str]:
            ...

        assert world[dummy] is dummy_impl2

    assert world[dummy] is dummy_impl

    with world.test.copy():
        assert dummy in world
        assert world[dummy] is dummy_impl

        @_(implements(dummy).when(weighted(10)))
        def dummy_impl2() -> Box[str]:
            ...

        assert world[dummy] is dummy_impl2

    assert world[dummy] is dummy_impl


def test_debug() -> None:
    namespace = f"tests.lib.interface.test_function.{test_debug.__name__}.<locals>"

    @interface
    def dummy() -> str:
        ...

    @_(implements(dummy).by_default)
    def dummy_default() -> str:
        ...

    assert world.debug(dummy.single()) == expected_debug(
        f"""
    ∅ <single> {namespace}.dummy
    └── 🟉 [Default] <const> {namespace}.dummy_default
    """
    )

    assert world.debug(dummy.all()) == expected_debug(
        f"""
    ∅ <all> {namespace}.dummy
    └── 🟉 [Default] <const> {namespace}.dummy_default
    """
    )

    @implements(dummy)
    def dummy_impl() -> str:
        ...

    assert world.debug(dummy) == expected_debug(
        f"""
    ∅ <single> {namespace}.dummy
    └── 🟉 <const> {namespace}.dummy_impl
    """
    )

    assert world.debug(dummy.single()) == expected_debug(
        f"""
    ∅ <single> {namespace}.dummy
    └── 🟉 <const> {namespace}.dummy_impl
    """
    )

    assert world.debug(dummy.all()) == expected_debug(
        f"""
    ∅ <all> {namespace}.dummy
    └── 🟉 <const> {namespace}.dummy_impl
    """
    )

    @_(implements(dummy).when(qualified_by="a"))
    def dummy_a() -> str:
        ...

    assert world.debug(dummy) == expected_debug(
        f"""
    ∅ <single> {namespace}.dummy
    ├── 🟉 [NeutralWeight] <const> {namespace}.dummy_a
    └── 🟉 [NeutralWeight] <const> {namespace}.dummy_impl
    """
    )

    assert world.debug(dummy.single(qualified_by="a")) == expected_debug(
        f"""
    ∅ <single> {namespace}.dummy // qualified_by=['a']
    └── 🟉 <const> {namespace}.dummy_a
    """
    )

    assert world.debug(dummy.single(qualified_by_one_of=["a"])) == expected_debug(
        f"""
    ∅ <single> {namespace}.dummy // qualified_by_one_of=['a']
    └── 🟉 <const> {namespace}.dummy_a
    """
    )


def test_unexpected_lazy() -> None:
    with pytest.raises(TypeError, match="lazy"):

        @interface
        @lazy
        def failure() -> None:
            ...

    @interface
    def dummy() -> None:
        ...

    with pytest.raises(TypeError, match="lazy"):

        @implements(dummy)  # type: ignore
        @lazy
        def dummy_impl() -> None:
            ...

    with pytest.raises(TypeError, match="lazy"):

        @overridable
        @lazy
        def dummy2() -> None:
            ...


def test_duplicate_interface() -> None:
    def dummy() -> None:
        ...

    interface(dummy)
    with pytest.raises(DuplicateDependencyError, match="dummy"):
        interface(dummy)

    with pytest.raises(DuplicateDependencyError, match="dummy"):
        overridable(dummy)
