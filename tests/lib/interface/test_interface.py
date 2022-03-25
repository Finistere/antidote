# pyright: reportUnusedClass=false
from __future__ import annotations

import sys
from typing import Any, Generic, Iterable, Iterator, List, Optional, Sequence, TypeVar

import pytest
from typing_extensions import Protocol, runtime_checkable

from antidote import ImplementationsOf, implements, inject, interface, service, world
from antidote._providers import ServiceProvider
from antidote.core.exceptions import DependencyInstantiationError, DependencyNotFoundError
from antidote.lib.interface import QualifiedBy, register_interface_provider

T = TypeVar('T')
Tco = TypeVar('Tco', covariant=True)


def _(x: T) -> T:
    return x


class Base:
    pass


class GenericBase(Generic[Tco]):
    pass


class GenericProtocolBase(Protocol[Tco]):
    pass


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
def setup_world() -> Iterator[None]:
    with world.test.empty():
        world.provider(ServiceProvider)
        register_interface_provider()
        yield


def test_single_implementation() -> None:
    interface(Base)

    @implements(Base)
    class Dummy(Base):
        pass

    # Dummy declared as a singleton
    dummy = world.get(Dummy)
    assert isinstance(dummy, Dummy)
    assert dummy is world.get(Dummy)

    # Base is implemented by Dummy
    assert world.get(Base) is dummy

    with pytest.raises(DependencyNotFoundError):
        world.get[object](ImplementationsOf(Base))

    assert world.get(ImplementationsOf[Base](Base).single()) is dummy
    assert world.get[Base].single() is dummy

    bases: Sequence[object] = world.get(ImplementationsOf[Base](Base).all())
    assert isinstance(bases, list)
    assert len(bases) == 1
    assert bases[0] is dummy

    assert world.get[Base].all() == bases

    @inject
    def single_base(x: Base = inject.me()) -> Base:
        return x

    assert single_base() is dummy

    @inject
    def all_bases(x: List[Base] = inject.me()) -> List[Base]:
        return x

    bases = all_bases()
    assert isinstance(bases, list)
    assert len(bases) == 1
    assert bases[0] is dummy

    if sys.version_info >= (3, 9):
        @inject
        def all_bases_type_alias(x: list[Base] = inject.me()) -> List[Base]:
            return x

        assert all_bases_type_alias() == all_bases()

    @inject
    def all_bases_sequence(x: Sequence[Base] = inject.me()) -> Sequence[Base]:
        return x

    assert all_bases_sequence() == all_bases()

    @inject
    def all_bases_iterable(x: Iterable[Base] = inject.me()) -> Iterable[Base]:
        return x

    assert all_bases_iterable() == all_bases()


def test_single_multiple_implementations_failure() -> None:
    interface(Base)

    @implements(Base)
    class Dummy(Base):
        pass

    @implements(Base)
    class Dummy2(Base):
        pass

    with pytest.raises(DependencyInstantiationError, match=".*Base.*"):
        world.get(Base)

    with pytest.raises(DependencyInstantiationError, match=".*Base.*"):
        world.get[Base].single()

    with pytest.raises(DependencyInstantiationError, match=".*Base.*"):
        @inject
        def f(x: Base = inject.me()) -> Base:
            return x  # pragma: no cover

        f()


def test_qualified_implementations() -> None:
    interface(Base)

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

    @_(implements(Base))
    class Void(Base):
        pass

    with pytest.raises(DependencyNotFoundError):
        world.get[object](ImplementationsOf(Base))

    with pytest.raises(DependencyInstantiationError):
        world.get[Base].single()

    with pytest.raises(DependencyInstantiationError):
        world.get(Base)

    with pytest.raises(DependencyInstantiationError):
        world.get[Base]()

    a = world.get(A)
    b = world.get(B)
    c = world.get(C)
    cd = world.get(CD)
    void = world.get(Void)

    # qualified_by
    assert world.get[Base].single(qualified_by=[qA]) is a
    assert world.get[Base].single(qualified_by=[qB]) is b

    assert world.get[Base].all() == [void, cd, c, b, a]
    assert world.get[Base].all(qualified_by=[qA]) == [a]
    assert world.get[Base].all(qualified_by=[qB]) == [b]

    @inject
    def f(x: Base = inject.me(qualified_by=[qA])) -> Base:
        return x

    assert f() is a

    @inject
    def f2(x: Base = inject.get[Base].single(qualified_by=[qA])) -> Base:
        return x

    assert f2() is a

    # qualified_b // impossible
    with pytest.raises(DependencyNotFoundError):
        world.get[Base].single(qualified_by=[qA, qB])

    assert set(world.get[Base].all(qualified_by=[qA, qB])) == set()

    # qualified_by // multiple
    assert world.get[Base].single(qualified_by=[sqC, qD]) is cd
    assert world.get[Base].all(qualified_by=[sqC, qD]) == [cd]

    # qualified_by_one_of
    assert world.get[Base].single(qualified_by_one_of=[qD]) is cd
    assert world.get[Base].all(qualified_by_one_of=[qD]) == [cd]

    with pytest.raises(DependencyInstantiationError):
        world.get[Base].single(qualified_by_one_of=[sqC])

    with pytest.raises(DependencyInstantiationError):
        world.get[Base].single(qualified_by_one_of=[qA, qB])

    assert world.get[Base].all(qualified_by_one_of=[sqC]) == [cd, c]
    assert world.get[Base].all(qualified_by_one_of=[qA, qB]) == [b, a]

    @inject
    def g(x: List[Base] = inject.me(qualified_by_one_of=[sqC])) -> List[Base]:
        return x

    assert g() == [cd, c]

    @inject
    def g2(x: List[Base] = inject.get[Base].all(qualified_by_one_of=[sqC])) -> List[Base]:
        return x

    assert g2() == [cd, c]

    # Constraints
    assert world.get[Base].single(QualifiedBy(qA)) is a
    assert world.get[Base].all(QualifiedBy(qA)) == [a]
    assert world.get[Base].single(QualifiedBy.one_of(qD)) is cd
    assert world.get[Base].all(QualifiedBy.one_of(sqC)) == [cd, c]

    # Mixed constraints
    assert world.get[Base].single(QualifiedBy.one_of(qD), QualifiedBy(sqC)) is cd
    assert world.get[Base].all(QualifiedBy.one_of(qD), QualifiedBy(sqC)) == [cd]
    assert world.get[Base].single(QualifiedBy.one_of(qD), QualifiedBy.one_of(sqC)) is cd
    assert world.get[Base].all(QualifiedBy.one_of(qD), QualifiedBy.one_of(sqC)) == [cd]


def test_invalid_interface() -> None:
    with pytest.raises(TypeError, match="(?i).*class.*"):
        interface(object())  # type: ignore

    with pytest.raises(TypeError, match="(?i).*class.*"):
        ImplementationsOf(object())  # type: ignore

    with pytest.raises(ValueError, match="(?i).*decorated.*@interface.*"):
        ImplementationsOf(Qualifier)


def test_invalid_implementation() -> None:
    interface(Base)

    class BaseImpl(Base):
        pass

    with pytest.raises(TypeError, match="(?i).*class.*implementation.*"):
        implements(Base)(object())  # type: ignore

    with pytest.raises(TypeError, match="(?i).*class.*interface.*"):
        implements(object())(BaseImpl)  # type: ignore

    with pytest.raises(TypeError, match="(?i).*instance.*Predicate.*"):
        implements(Base).when(object())(BaseImpl)  # type: ignore

    # should work
    implements(Base)(BaseImpl)


def test_unique_predicate() -> None:
    interface(Base)

    class MyPred:
        def weight(self) -> Optional[Any]:
            return None

    with pytest.raises(RuntimeError, match="(?i).*unique.*"):
        @_(implements(Base).when(MyPred(), MyPred()))
        class BaseImpl(Base):
            pass

    # should work
    @_(implements(Base).when(MyPred()))
    class BaseImplV2(Base):
        pass


def test_custom_service() -> None:
    interface(Base)

    @implements(Base)
    @service(singleton=False)
    class BaseImpl(Base):
        pass

    # is a singleton
    assert world.get(BaseImpl) is not world.get(BaseImpl)
    assert isinstance(world.get[Base].single(), BaseImpl)


def test_type_enforcement_if_possible() -> None:
    interface(Base)

    with pytest.raises(TypeError, match="(?i).*subclass.*Base.*"):
        @implements(Base)
        class Invalid1:
            pass

    @interface
    class BaseProtocol(Protocol):
        def method(self) -> None:
            pass  # pragma: no cover

    @implements(BaseProtocol)
    class Invalid2:
        pass

    @interface
    @runtime_checkable
    class RuntimeProtocol(Protocol):
        def method(self) -> None:
            pass  # pragma: no cover

    with pytest.raises(TypeError, match="(?i).*protocol.*RuntimeProtocol.*"):
        @implements(RuntimeProtocol)
        class Invalid3:
            pass


def test_generic():
    interface(GenericBase)

    @implements(GenericBase)
    class Dummy(GenericBase[int]):
        pass

    dummy = world.get(Dummy)
    assert world.get(GenericBase) is dummy
    assert world.get[GenericBase].single() is dummy
    assert world.get[GenericBase].all() == [dummy]

    @inject
    def f(x: GenericBase[int] = inject.me()) -> GenericBase[int]:
        return x

    assert f() is dummy

    @inject
    def f_all(x: List[GenericBase[int]] = inject.me()) -> List[GenericBase[int]]:
        return x

    assert f_all() == [dummy]


def test_generic_protocol():
    interface(GenericProtocolBase)

    @implements(GenericProtocolBase)
    class Dummy:
        pass

    dummy = world.get(Dummy)
    assert world.get(GenericProtocolBase) is dummy
    assert world.get[GenericProtocolBase].single() is dummy
    assert world.get[GenericProtocolBase].all() == [dummy]

    @inject
    def f(x: GenericProtocolBase[int] = inject.me()) -> GenericProtocolBase[int]:
        return x

    assert f() is dummy

    @inject
    def f_all(x: List[GenericProtocolBase[int]] = inject.me()) -> List[GenericProtocolBase[int]]:
        return x

    assert f_all() == [dummy]
