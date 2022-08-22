# pyright: reportUnusedClass=false, reportUnusedFunction=false
from __future__ import annotations

import sys
from typing import Generic, Iterable, List, Sequence, TypeVar

import pytest
from typing_extensions import Protocol, runtime_checkable

from antidote import (
    AmbiguousImplementationChoiceError,
    antidote_lib_injectable,
    antidote_lib_interface,
    DependencyNotFoundError,
    DuplicateDependencyError,
    FrozenCatalogError,
    implements,
    inject,
    injectable,
    instanceOf,
    interface,
    new_catalog,
    QualifiedBy,
    SingleImplementationNotFoundError,
    Wiring,
    world,
)
from tests.lib.interface.common import _, weighted
from tests.utils import expected_debug

Tco = TypeVar("Tco", covariant=True)


class Qualifier:
    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"Qualifier({self.name})"


class SubQualifier(Qualifier):
    pass


qA = Qualifier("qA")
qB = Qualifier("qB")
sqC = SubQualifier("qC")
qD = Qualifier("qD")


@pytest.fixture(autouse=True)
def setup_world() -> None:
    world.include(antidote_lib_injectable)
    world.include(antidote_lib_interface)


def test_single_implementation() -> None:
    @interface
    class Base:
        pass

    @implements(Base)
    class Dummy(Base):
        pass

    with pytest.raises(TypeError, match="@implements"):
        implements.lazy(Base)  # type: ignore

    # not accessible directly
    assert Dummy not in world
    assert Base in world
    assert instanceOf[Base] in world
    assert instanceOf[Base]().single() in world
    dummy = world[Base]
    assert isinstance(dummy, Dummy)
    # singleton
    assert world[Base] is dummy
    assert world[instanceOf[Base]] is dummy
    assert world[instanceOf[Base]()] is dummy
    assert world[instanceOf(Base)] is dummy
    assert world[instanceOf(Base).single()] is dummy
    assert world[instanceOf[Base]().single()] is dummy
    assert world[instanceOf(Base).single()] is dummy
    assert world[instanceOf(Base).all()] == [dummy]
    assert world[instanceOf[Base]().all()] == [dummy]
    assert world[instanceOf(Base).all()] == [dummy]

    @inject
    def single_base(x: Base = inject.me()) -> Base:
        return x

    assert single_base() is dummy

    @inject
    def all_bases(x: List[Base] = inject.me()) -> List[Base]:
        return x

    assert all_bases() == [dummy]

    if sys.version_info >= (3, 9):

        @inject
        def all_bases_type_alias(x: list[Base] = inject.me()) -> List[Base]:
            return x

        assert all_bases_type_alias() == [dummy]

    @inject
    def all_bases_sequence(x: Sequence[Base] = inject.me()) -> Sequence[Base]:
        return x

    assert all_bases_sequence() == [dummy]

    @inject
    def all_bases_iterable(x: Iterable[Base] = inject.me()) -> Iterable[Base]:
        return x

    assert all_bases_iterable() == [dummy]


def test_single_multiple_implementations_failure() -> None:
    @interface
    class Base:
        pass

    @implements(Base)
    class Dummy(Base):
        pass

    @implements(Base)
    class Dummy2(Base):
        pass

    with pytest.raises(AmbiguousImplementationChoiceError, match="Base"):
        world[Base]

    with pytest.raises(AmbiguousImplementationChoiceError, match="Base"):
        world[instanceOf(Base).single()]

    with pytest.raises(AmbiguousImplementationChoiceError, match="Base"):

        @inject
        def f(x: Base = inject.me()) -> Base:
            return x  # pragma: no cover

        f()


def test_qualified_implementations() -> None:
    @interface
    class Base:
        pass

    @_(implements(Base).when(qualified_by=qA))
    class A(Base):
        pass

    @_(implements(Base).when(qualified_by=qB))
    class B(Base):
        pass

    @_(implements(Base).when(qualified_by=[sqC]))
    class C(Base):
        pass

    @_(implements(Base).when(qualified_by=[sqC, qD]))
    class CD(Base):
        pass

    with pytest.raises(AmbiguousImplementationChoiceError, match="Base"):
        world[instanceOf(Base)]

    with pytest.raises(AmbiguousImplementationChoiceError, match="Base"):
        world[instanceOf(Base).single()]

    with pytest.raises(AmbiguousImplementationChoiceError, match="Base"):
        world[Base]

    a = world[instanceOf(Base).single(qualified_by=qA)]
    assert isinstance(a, A)
    assert world[instanceOf(Base).single(qualified_by=[qA])] is a
    assert world[instanceOf[Base]().single(qualified_by=qA)] is a
    assert world[instanceOf[Base]().single(qualified_by=[qA])] is a

    b = world[instanceOf(Base).single(qualified_by=qB)]
    assert isinstance(b, B)
    cd = world[instanceOf(Base).single(qualified_by=[sqC, qD])]
    assert isinstance(cd, CD)

    c_bases = world[instanceOf(Base).all(qualified_by=sqC)]
    c = next(e for e in c_bases if isinstance(e, C))
    # ordering is not part of the spec though.
    assert c_bases == [cd, c]

    assert world[instanceOf(Base).all()] == [cd, c, b, a]
    assert world[instanceOf(Base).all(qualified_by=[qA])] == [a]
    assert world[instanceOf(Base).all(qualified_by=[qB])] == [b]

    @inject
    def f(x: Base = inject.me(qualified_by=[qA])) -> Base:
        return x

    assert f() is a

    @inject
    def f2(x: Base = inject[instanceOf(Base).single(qualified_by=[qA])]) -> Base:
        return x

    assert f2() is a

    # qualified_b // impossible
    with pytest.raises(SingleImplementationNotFoundError):
        world[instanceOf(Base).single(qualified_by=[qA, qB])]

    assert set(world[instanceOf(Base).all(qualified_by=[qA, qB])]) == set()

    # qualified_by // multiple
    assert world[instanceOf(Base).single(qualified_by=[sqC, qD])] is cd
    assert world[instanceOf(Base).all(qualified_by=[sqC, qD])] == [cd]

    # qualified_by_one_of
    assert world[instanceOf(Base).single(qualified_by_one_of=[qD])] is cd
    assert world[instanceOf(Base).all(qualified_by_one_of=[qD])] == [cd]

    with pytest.raises(AmbiguousImplementationChoiceError):
        world[instanceOf(Base).single(qualified_by_one_of=[sqC])]

    with pytest.raises(AmbiguousImplementationChoiceError):
        world[instanceOf(Base).single(qualified_by_one_of=[qA, qB])]

    assert world[instanceOf(Base).all(qualified_by_one_of=[sqC])] == [cd, c]
    assert world[instanceOf(Base).all(qualified_by_one_of=[qA, qB])] == [b, a]

    @inject
    def g(x: Sequence[Base] = inject.me(qualified_by_one_of=[sqC])) -> Sequence[Base]:
        return x

    assert g() == [cd, c]

    @inject
    def g2(
        x: Sequence[Base] = inject[instanceOf(Base).all(qualified_by_one_of=[sqC])],
    ) -> Sequence[Base]:
        return x

    assert g2() == [cd, c]

    # Constraints
    assert world[instanceOf(Base).single(QualifiedBy(qA))] is a
    assert world[instanceOf(Base).all(QualifiedBy(qA))] == [a]
    assert world[instanceOf(Base).single(QualifiedBy.one_of(qD))] is cd
    assert world[instanceOf(Base).all(QualifiedBy.one_of(sqC))] == [cd, c]

    # Mixed constraints
    assert world[instanceOf(Base).single(QualifiedBy.one_of(qD), QualifiedBy(sqC))] is cd
    assert world[instanceOf(Base).all(QualifiedBy.one_of(qD), QualifiedBy(sqC))] == [cd]
    assert world[instanceOf(Base).single(QualifiedBy.one_of(qD), QualifiedBy.one_of(sqC))] is cd
    assert world[instanceOf(Base).all(QualifiedBy.one_of(qD), QualifiedBy.one_of(sqC))] == [cd]


def test_invalid_interface() -> None:
    with pytest.raises(TypeError, match="class.*function"):
        interface(object())  # type: ignore


def test_invalid_implementation() -> None:
    @interface
    class Base:
        pass

    class BaseImpl(Base):
        pass

    with pytest.raises(TypeError, match="class.*implementation"):
        implements(Base)(object())  # type: ignore

    with pytest.raises(TypeError, match="(?i)interface"):
        implements(object())(BaseImpl)  # type: ignore

    with pytest.raises(TypeError, match="predicate"):
        implements(Base).when(object())(BaseImpl)  # type: ignore

    # should work
    implements(Base)(BaseImpl)


def test_unknown_interface() -> None:
    class Base:
        pass

    with pytest.raises(DependencyNotFoundError, match="interface.*Base"):

        @implements(Base)
        class BaseImpl(Base):
            ...


def test_custom_injectable() -> None:
    @interface
    class Base:
        pass

    @_(implements(Base).as_default)
    @injectable(lifetime="transient")
    class Default(Base):
        pass

    # is a singleton
    assert world[Default] is not world[Default]
    assert isinstance(world[instanceOf(Base).single()], Default)

    @implements(Base)
    @injectable(lifetime="transient")
    class BaseImpl(Base):
        pass

    # is not a singleton
    assert world[BaseImpl] is not world[BaseImpl]
    assert isinstance(world[instanceOf(Base).single()], BaseImpl)

    @_(implements(Base).overriding(BaseImpl))
    @injectable(lifetime="transient")
    class Custom(Base):
        pass

    # is not a singleton
    assert world[Custom] is not world[Custom]
    assert isinstance(world[instanceOf(Base).single()], Custom)

    @interface
    class Base2:
        pass

    @implements(Base2)
    @injectable
    class Dummy(Base2):
        pass

    assert world[Base2] is world[Dummy]


def test_protocol() -> None:
    @interface
    class Base(Protocol):
        pass

    @_(implements.protocol[Base]())
    class Impl:
        pass

    assert isinstance(world[instanceOf[Base]], Impl)


def test_type_enforcement_if_possible() -> None:
    @interface
    class Base:
        pass

    with pytest.raises(TypeError, match="subclass.*Base"):

        @implements(Base)
        class Invalid1:
            pass

    @interface
    class BaseProtocol(Protocol):
        def method(self) -> None:
            pass  # pragma: no cover

    @_(implements.protocol[BaseProtocol]())
    class Invalid2:
        pass

    @interface
    @runtime_checkable
    class RuntimeProtocol(Protocol):
        def method(self) -> None:
            pass  # pragma: no cover

    with pytest.raises(TypeError, match="protocol.*RuntimeProtocol"):

        @_(implements.protocol[RuntimeProtocol]())
        class Invalid3:
            pass


def test_generic() -> None:
    @interface
    class GenericBase(Generic[Tco]):
        pass

    @implements(GenericBase[int])
    class Dummy(GenericBase[int]):
        pass

    dummy = world[GenericBase[int]]
    assert isinstance(dummy, Dummy)
    assert world[GenericBase] is dummy
    assert world[instanceOf(GenericBase).single()] is dummy  # pyright: ignore
    assert world[instanceOf(GenericBase).all()] == [dummy]  # pyright: ignore
    assert world[instanceOf(GenericBase[int]).single()] is dummy
    assert world[instanceOf(GenericBase[int]).all()] == [dummy]

    @inject
    def f(x: GenericBase[int] = inject.me()) -> GenericBase[int]:
        return x

    assert f() is dummy

    @inject
    def f_all(x: List[GenericBase[int]] = inject.me()) -> List[GenericBase[int]]:
        return x

    assert f_all() == [dummy]


def test_generic_protocol() -> None:
    @interface
    class GenericProtocolBase(Protocol[Tco]):
        pass

    @implements(GenericProtocolBase)  # type: ignore
    class Dummy1:
        pass

    @_(implements.protocol[GenericProtocolBase[int]]().overriding(Dummy1))
    class Dummy:
        pass

    dummy = world[instanceOf[GenericProtocolBase[int]]]
    assert isinstance(dummy, Dummy)
    assert world[instanceOf[GenericProtocolBase]] is dummy  # type: ignore
    assert world[instanceOf[GenericProtocolBase]()] is dummy  # type: ignore
    assert world[instanceOf[GenericProtocolBase]().single()] is dummy  # type: ignore
    assert world[instanceOf[GenericProtocolBase]().all()] == [dummy]  # type: ignore
    assert world[instanceOf[GenericProtocolBase[int]]] is dummy
    assert world[instanceOf[GenericProtocolBase[int]]()] is dummy
    assert world[instanceOf[GenericProtocolBase[int]]().single()] is dummy
    assert world[instanceOf[GenericProtocolBase[int]]().all()] == [dummy]

    @inject
    def f(x: GenericProtocolBase[int] = inject.me()) -> GenericProtocolBase[int]:
        return x

    assert f() is dummy

    @inject
    def f_all(x: List[GenericProtocolBase[int]] = inject.me()) -> List[GenericProtocolBase[int]]:
        return x

    assert f_all() == [dummy]


def test_overriding() -> None:
    @interface
    class Base:
        ...

    @implements(Base)
    class Default(Base):
        ...

    default = world[Base]
    assert isinstance(default, Default)

    @_(implements(Base).overriding(Default))
    class Custom(Base):
        ...

    assert Custom not in world
    custom = world[Base]
    assert isinstance(custom, Custom)

    with pytest.raises(ValueError, match="Default"):

        @_(implements(Base).overriding(Default))
        class CustomV2(Base):
            ...

    with pytest.raises(TypeError, match="class"):
        implements(Base).overriding(object())  # type: ignore


def test_by_default() -> None:
    @interface
    class Base:
        ...

    @_(implements(Base).as_default)
    class Default(Base):
        ...

    with pytest.raises(RuntimeError, match="(?i)default dependency"):

        @_(implements(Base).as_default)
        class Default2(Base):
            ...

    assert Default not in world
    default = world[Base]
    assert isinstance(default, Default)
    assert world[instanceOf(Base).single()] is default
    assert world[instanceOf(Base).all()] == [default]

    @_(implements(Base))
    class Dummy(Base):
        ...

    dummy = world[Base]
    assert isinstance(dummy, Dummy)
    assert world[instanceOf(Base).single()] is dummy
    assert world[instanceOf(Base).all()] == [dummy]


def test_overridable() -> None:
    @interface.as_default
    class Base:
        pass

    impl = world[Base]
    assert isinstance(impl, Base)
    assert world[instanceOf(Base).single()] is impl
    assert world[instanceOf(Base).all()] == [impl]

    with pytest.raises(RuntimeError, match="(?i)default dependency"):

        @_(implements(Base).as_default)
        class Default2(Base):
            ...

    @_(implements(Base).overriding(Base))
    class Default(Base):
        pass

    default = world[Base]
    assert isinstance(default, Default)
    assert world[instanceOf(Base).single()] is default
    assert world[instanceOf(Base).all()] == [default]

    @_(implements(Base))
    class Dummy(Base):
        pass

    dummy = world[Base]
    assert isinstance(dummy, Dummy)
    assert world[instanceOf(Base).single()] is dummy
    assert world[instanceOf(Base).all()] == [dummy]

    with pytest.raises(TypeError, match="class.*function"):
        interface.as_default(object())  # type: ignore


def test_by_default_overriding() -> None:
    @interface
    class Base:
        ...

    @_(implements(Base).as_default)
    class Default(Base):
        ...

    @_(implements(Base).overriding(Default))
    class Custom(Base):
        ...

    custom = world[Base]
    assert isinstance(custom, Custom)
    assert world[instanceOf(Base).single()] is custom
    assert world[instanceOf(Base).all()] == [custom]


def test_invalid_instanceOf() -> None:
    with pytest.raises(TypeError, match="interface.*class"):
        instanceOf(object())  # type: ignore


def test_injection_and_type_hints() -> None:
    @injectable(catalog=world.private)
    class Dep:
        pass

    with pytest.raises(NameError, match="Dep"):

        @interface.as_default(type_hints_locals=None)
        class Failure:
            def f(self, dep: Dep = inject.me()) -> object:
                ...

    injected = world.private[Dep]
    not_injected = inject.me()

    @interface.as_default
    class Dummy:
        def f(self, dep: Dep = inject.me()) -> object:
            return dep

    @interface.as_default
    class DummyCustom:
        @inject(kwargs=dict(dep=Dep))
        def f(self, dep: object = None) -> object:
            return dep

    @interface.as_default(wiring=None)
    class DummyNone:
        def f(self, dep: Dep = inject.me()) -> object:
            return dep

    @interface.as_default
    @injectable(wiring=None)
    class DummyInjectableNone:
        def f(self, dep: Dep = inject.me()) -> object:
            return dep

    assert world[Dummy].f() == injected
    assert world[DummyCustom].f() == injected
    assert world[DummyNone].f() == not_injected
    assert world[DummyInjectableNone].f() == not_injected
    assert Dummy().f() == injected
    assert DummyCustom().f() == injected
    assert DummyNone().f() == not_injected
    assert DummyInjectableNone().f() == not_injected

    @implements(Dummy)
    class DummyImpl(Dummy):
        def f(self, dep: Dep = inject.me()) -> object:
            return "impl", dep

    @implements(DummyCustom)
    class DummyCustomImpl(DummyCustom):
        @inject(kwargs=dict(dep=Dep))
        def f(self, dep: object = None) -> object:
            return "impl", dep

    @implements(DummyNone, wiring=None)
    class DummyNoneImpl(DummyNone):
        def f(self, dep: Dep = inject.me()) -> object:
            return "impl", dep

    @implements(DummyInjectableNone)
    @injectable(wiring=None)
    class DummyInjectableNoneImpl(DummyInjectableNone):
        def f(self, dep: Dep = inject.me()) -> object:
            return "impl", dep

    assert world[Dummy].f() == ("impl", injected)
    assert world[DummyCustom].f() == ("impl", injected)
    assert world[DummyNone].f() == ("impl", not_injected)
    assert world[DummyInjectableNone].f() == ("impl", not_injected)
    assert DummyImpl().f() == ("impl", injected)
    assert DummyCustomImpl().f() == ("impl", injected)
    assert DummyNoneImpl().f() == ("impl", not_injected)
    assert DummyInjectableNoneImpl().f() == ("impl", not_injected)

    @_(implements(Dummy).overriding(DummyImpl))
    class DummyOverride(Dummy):
        def f(self, dep: Dep = inject.me()) -> object:
            return "override", dep

    @_(implements(DummyCustom).overriding(DummyCustomImpl))
    class DummyCustomOverride(DummyCustom):
        @inject(kwargs=dict(dep=Dep))
        def f(self, dep: object = None) -> object:
            return "override", dep

    @_(implements(DummyNone, wiring=None).overriding(DummyNoneImpl))
    class DummyNoneOverride(DummyNone):
        def f(self, dep: Dep = inject.me()) -> object:
            return "override", dep

    @_(implements(DummyInjectableNone).overriding(DummyInjectableNoneImpl))
    @injectable(wiring=None)
    class DummyInjectableNoneOverride(DummyInjectableNone):
        def f(self, dep: Dep = inject.me()) -> object:
            return "override", dep

    assert world[Dummy].f() == ("override", injected)
    assert world[DummyCustom].f() == ("override", injected)
    assert world[DummyNone].f() == ("override", not_injected)
    assert world[DummyInjectableNone].f() == ("override", not_injected)
    assert DummyOverride().f() == ("override", injected)
    assert DummyCustomOverride().f() == ("override", injected)
    assert DummyNoneOverride().f() == ("override", not_injected)
    assert DummyInjectableNoneOverride().f() == ("override", not_injected)

    @_(implements(Dummy).when(weighted(12)))
    class DummyWhen(Dummy):
        def f(self, dep: Dep = inject.me()) -> object:
            return "when", dep

    @_(implements(DummyCustom).when(weighted(12)))
    class DummyCustomWhen(DummyCustom):
        @inject(kwargs=dict(dep=Dep))
        def f(self, dep: object = None) -> object:
            return "when", dep

    @_(implements(DummyNone, wiring=None).when(weighted(12)))
    class DummyNoneWhen(DummyNone):
        def f(self, dep: Dep = inject.me()) -> object:
            return "when", dep

    @_(implements(DummyInjectableNone).when(weighted(12)))
    @injectable(wiring=None)
    class DummyInjectableNoneWhen(DummyInjectableNone):
        def f(self, dep: Dep = inject.me()) -> object:
            return "when", dep

    assert world[Dummy].f() == ("when", injected)
    assert world[DummyCustom].f() == ("when", injected)
    assert world[DummyNone].f() == ("when", not_injected)
    assert world[DummyInjectableNone].f() == ("when", not_injected)
    assert DummyWhen().f() == ("when", injected)
    assert DummyCustomWhen().f() == ("when", injected)
    assert DummyNoneWhen().f() == ("when", not_injected)
    assert DummyInjectableNoneWhen().f() == ("when", not_injected)


def test_catalog() -> None:
    catalog = new_catalog(include=[antidote_lib_interface])

    @interface(catalog=catalog)
    class Base:
        ...

    @implements(Base, catalog=catalog)
    class Impl(Base):
        ...

    assert isinstance(catalog[Base], Impl)
    assert Base not in world

    with pytest.raises(TypeError, match="catalog"):
        interface(catalog=object())  # type: ignore

    with pytest.raises(TypeError, match="catalog"):
        implements(Base, catalog=object())  # type: ignore

    @interface.as_default(catalog=catalog)
    class Base2:
        ...

    assert isinstance(catalog[Base2], Base2)
    assert Base2 not in world

    with pytest.raises(TypeError, match="catalog"):
        interface.as_default(catalog=object())  # type: ignore


def test_frozen() -> None:
    @interface
    class Dummy:
        pass

    @implements(Dummy)
    class DummyImpl(Dummy):
        pass

    world.freeze()

    with pytest.raises(FrozenCatalogError):

        @interface
        class Failure:
            pass

    with pytest.raises(FrozenCatalogError):

        @implements(Dummy)
        class DummyFailure(Dummy):
            pass

    with pytest.raises(FrozenCatalogError):

        @_(implements(Dummy).when(True))
        class DummyFailure2(Dummy):
            pass

    with pytest.raises(FrozenCatalogError):

        @_(implements(Dummy).when(False))
        class DummyFailure3(Dummy):
            pass

    with pytest.raises(FrozenCatalogError):

        @_(implements(Dummy).as_default)
        class DummyFailure4(Dummy):
            pass

    with pytest.raises(FrozenCatalogError):

        @_(implements(Dummy).overriding(DummyImpl))
        class DummyFailure5(Dummy):
            pass


def test_test_env() -> None:
    @interface
    class Dummy:
        pass

    @_(implements(Dummy).as_default)
    class DummyDefault(Dummy):
        ...

    original_default = world[Dummy]

    with world.test.empty():
        assert Dummy not in world

    assert world[Dummy] is original_default

    with world.test.new():
        assert Dummy not in world

    assert world[Dummy] is original_default

    with world.test.clone():
        assert Dummy in world
        result = world[Dummy]
        assert isinstance(result, DummyDefault)
        assert result is not original_default

        with pytest.raises(FrozenCatalogError):

            @_(implements(Dummy).overriding(DummyDefault))
            class Failure(Dummy):
                ...

    assert world[Dummy] is original_default

    with world.test.clone(frozen=False):
        assert Dummy in world
        result = world[Dummy]
        assert isinstance(result, DummyDefault)
        assert result is not original_default

        @_(implements(Dummy).overriding(DummyDefault))
        class DummyDefault2(Dummy):
            ...

        assert isinstance(world[Dummy], DummyDefault2)

    assert world[Dummy] is original_default

    with world.test.copy():
        assert Dummy in world
        result = world[Dummy]
        assert isinstance(result, DummyDefault)
        assert result is original_default

        with pytest.raises(FrozenCatalogError):

            @_(implements(Dummy).overriding(DummyDefault))
            class Failure2(Dummy):
                ...

    assert world[Dummy] is original_default

    with world.test.copy(frozen=False):
        assert Dummy in world
        result = world[Dummy]
        assert isinstance(result, DummyDefault)
        assert result is original_default

        @_(implements(Dummy).overriding(DummyDefault))
        class DummyDefault3(Dummy):
            ...

        assert isinstance(world[Dummy], DummyDefault3)

    assert world[Dummy] is original_default

    @implements(Dummy)
    class DummyImpl(Dummy):
        ...

    original = world[Dummy]

    with world.test.empty():
        assert Dummy not in world

    assert world[Dummy] is original

    with world.test.new():
        assert Dummy not in world

    assert world[Dummy] is original

    with world.test.clone():
        assert Dummy in world
        result = world[Dummy]
        assert isinstance(result, DummyImpl)
        assert result is not original

        with pytest.raises(FrozenCatalogError):

            @_(implements(Dummy).overriding(DummyImpl))
            class Failure3(Dummy):
                ...

    assert world[Dummy] is original

    with world.test.clone(frozen=False):
        assert Dummy in world
        result = world[Dummy]
        assert isinstance(result, DummyImpl)
        assert result is not original

        @_(implements(Dummy).overriding(DummyImpl))
        class DummyImpl2(Dummy):
            ...

        assert isinstance(world[Dummy], DummyImpl2)

    assert world[Dummy] is original

    with world.test.copy():
        assert Dummy in world
        result = world[Dummy]
        assert isinstance(result, DummyImpl)
        assert result is original

        with pytest.raises(FrozenCatalogError):

            @_(implements(Dummy).overriding(DummyImpl))
            class Failure4(Dummy):
                ...

    assert world[Dummy] is original

    with world.test.copy(frozen=False):
        assert Dummy in world
        result = world[Dummy]
        assert isinstance(result, DummyImpl)
        assert result is original

        @_(implements(Dummy).overriding(DummyImpl))
        class DummyImpl3(Dummy):
            ...

        assert isinstance(world[Dummy], DummyImpl3)

    assert world[Dummy] is original


def test_debug() -> None:
    @interface
    class Base:
        pass

    @implements(Base)
    class Impl(Base):
        pass

    namespace = f"tests.lib.interface.test_class.{test_debug.__name__}.<locals>"

    assert world.debug(Base) == expected_debug(
        f"""
    ∅ <single> {namespace}.Base
    └── 🟉 {namespace}.Impl
    """
    )

    assert world.debug(instanceOf[Base]) == expected_debug(
        f"""
    ∅ <single> {namespace}.Base
    └── 🟉 {namespace}.Impl
    """
    )

    assert world.debug(instanceOf[Base]().single()) == expected_debug(
        f"""
    ∅ <single> {namespace}.Base
    └── 🟉 {namespace}.Impl
    """
    )

    @implements(Base)
    class Impl2(Base):
        pass

    assert world.debug(instanceOf[Base]().all()) == expected_debug(
        f"""
    ∅ <all> {namespace}.Base
    ├── 🟉 [NeutralWeight] {namespace}.Impl2
    └── 🟉 [NeutralWeight] {namespace}.Impl
    """
    )


def test_unexpected_wiring() -> None:
    @interface
    class Dummy:
        pass

    with pytest.raises(RuntimeError, match="already exists.*wiring"):

        @implements(Dummy, wiring=Wiring())
        @injectable
        class DummyImpl(Dummy):
            pass

    with pytest.raises(RuntimeError, match="already exists.*wiring"):

        @interface.as_default(wiring=Wiring())
        @injectable
        class Dummy2:
            pass


def test_duplicate_interface() -> None:
    class Base:
        pass

    interface(Base)
    with pytest.raises(DuplicateDependencyError, match="Base"):
        interface(Base)

    with pytest.raises(DuplicateDependencyError, match="Base"):
        interface.as_default(Base)
