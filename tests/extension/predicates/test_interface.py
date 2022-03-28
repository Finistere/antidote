import pytest

from antidote import implements, interface, world
from antidote._internal.world import WorldGet
from antidote._providers import ServiceProvider
from antidote.core.exceptions import DependencyInstantiationError, DependencyNotFoundError
from antidote.extension.predicates import QualifiedBy, register_interface_provider


def _(x):
    return x


class Qualifier:
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"Qualifier({self.name})"


class SubQualifier(Qualifier):
    pass


qA = Qualifier("qA")
qB = Qualifier("qB")
sqC = SubQualifier("qC")
qD = Qualifier("qD")


@pytest.fixture(params=['typed_get', 'interface'])
def get(request) -> WorldGet:
    if request.param == 'typed_get':
        return world.get
    else:
        class Query:
            def __init__(self, interface):
                self.interface = interface

            def single(self, *args, **kwargs):
                return world.get(interface[self.interface].single(*args, **kwargs))

            def all(self, *args, **kwargs):
                return world.get(interface[self.interface].all(*args, **kwargs))

        class Getter:
            def __getitem__(self, interface):
                return Query(interface)

        return Getter()  # type: ignore


@pytest.fixture(autouse=True)
def setup_world():
    with world.test.empty():
        world.provider(ServiceProvider)
        register_interface_provider()
        yield


def test_single_implementation():
    @interface
    class Base:
        pass

    @implements(Base)
    class Dummy(Base):
        pass

    # Dummy declared as a singleton
    dummy = world.get(Dummy)
    assert isinstance(dummy, Dummy)
    assert dummy is world.get(Dummy)

    # Base is implemented by Dummy
    assert world.get(Base) is dummy
    assert world.get(interface[Base]) is dummy
    assert world.get(interface[Base].single()) is dummy
    assert world.get[Base].single() is dummy

    bases = world.get(interface[Base].all())
    assert isinstance(bases, list)
    assert len(bases) == 1
    assert bases[0] is dummy

    assert world.get[Base].all() == bases


def test_qualified_implementations(get):
    @interface
    class Base:
        pass

    @_(implements(Base).when(qualified_by=[qA]))
    class A(Base):
        pass

    @_(implements(Base).when(qualified_by=[qB]))
    class B(Base):
        pass

    @_(implements(Base).when(qualified_by=[sqC]))
    class C(Base):
        pass

    @_(implements(Base).when(qualified_by=[sqC, qD]))
    class CD(Base):
        pass

    with pytest.raises(DependencyInstantiationError):
        world.get(Base)

    with pytest.raises(DependencyInstantiationError):
        world.get(interface[Base])

    with pytest.raises(DependencyInstantiationError):
        world.get[Base]()

    with pytest.raises(DependencyInstantiationError):
        get[Base].single()

    a = world.get(A)
    b = world.get(B)
    c = world.get(C)
    cd = world.get(CD)

    # qualified_by
    assert get[Base].single(qualified_by=[qA]) is a
    assert get[Base].single(qualified_by=[qB]) is b

    assert set(get[Base].all()) == {a, b, c, cd}
    assert get[Base].all(qualified_by=[qA]) == [a]
    assert get[Base].all(qualified_by=[qB]) == [b]

    # qualified_b // impossible
    with pytest.raises(DependencyNotFoundError):
        get[Base].single(qualified_by=[qA, qB])

    assert set(get[Base].all(qualified_by=[qA, qB])) == set()

    # qualified_by // multiple
    assert get[Base].single(qualified_by=[sqC, qD]) is cd
    assert get[Base].all(qualified_by=[sqC, qD]) == [cd]

    # qualified_by_one_of
    assert get[Base].single(qualified_by_one_of=[qD]) is cd
    assert get[Base].all(qualified_by_one_of=[qD]) == [cd]

    with pytest.raises(DependencyInstantiationError):
        get[Base].single(qualified_by_one_of=[sqC])

    with pytest.raises(DependencyInstantiationError):
        get[Base].single(qualified_by_one_of=[qA, qB])

    assert set(get[Base].all(qualified_by_one_of=[sqC])) == {c, cd}
    assert set(get[Base].all(qualified_by_one_of=[qA, qB])) == {a, b}

    # qualified_by_instance_of
    with pytest.raises(DependencyInstantiationError):
        get[Base].single(qualified_by_instance_of=SubQualifier)

    assert set(get[Base].all(qualified_by_instance_of=SubQualifier)) == {c, cd}
    assert set(get[Base].all(qualified_by_instance_of=Qualifier)) == {a, b, c, cd}

    # Constraints
    assert get[Base].single(QualifiedBy(qA)) is a
    assert get[Base].all(QualifiedBy(qA)) == [a]
    assert get[Base].single(QualifiedBy.one_of(qD)) is cd
    assert set(get[Base].all(QualifiedBy.one_of(sqC))) == {c, cd}
    assert set(get[Base].all(QualifiedBy.instance_of(SubQualifier))) == {c, cd}

    # Mixed constraints
    assert get[Base].single(QualifiedBy.one_of(qD), QualifiedBy.instance_of(SubQualifier)) is cd
    assert get[Base].all(QualifiedBy.one_of(qD), QualifiedBy.instance_of(SubQualifier)) == [cd]
    assert get[Base].single(QualifiedBy.one_of(qD), QualifiedBy.one_of(sqC)) is cd
    assert get[Base].all(QualifiedBy.one_of(qD), QualifiedBy.one_of(sqC)) == [cd]
