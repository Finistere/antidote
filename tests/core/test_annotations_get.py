from typing import Type

import pytest
from typing_extensions import Annotated

from antidote import factory, Get, inject, service, world


@pytest.fixture(autouse=True)
def new_world():
    with world.test.new():
        yield


def test_injectable():
    @service
    class Dummy:
        pass

    @inject(dependencies=[Get(Dummy)])
    def f(x):
        return x

    @inject(dependencies=[Get(Dummy)])
    def g(x: Annotated[Dummy, Get(Dummy)]):
        return x

    assert f() is world.get(Dummy)
    assert g() is world.get(Dummy)


def test_nested_get():
    @service
    class Dummy:
        pass

    @inject(dependencies=[Get(Get(Dummy))])
    def f(x):
        return x

    @inject
    def g(x: Annotated[Dummy, Get(Get(Dummy))]):
        return x

    assert f() is world.get(Dummy)
    assert g() is world.get(Dummy)


def test_factory():
    class Dummy:
        pass

    dummy = Dummy()

    @factory
    def build_dummy() -> Dummy:
        return dummy

    @inject(dependencies=[Get(Dummy, source=build_dummy)])
    def f(x):
        return x

    @inject
    def g(x: Annotated[Dummy, Get(Dummy, source=build_dummy)]):
        return x

    assert f() is dummy
    assert g() is dummy


def test_source():
    class Dummy:
        pass

    class DummySource:
        SENTINEL = Dummy()

        def __antidote_dependency__(self, dependency: Type[Dummy]) -> object:
            return self.SENTINEL

    dummy_source = DummySource()
    world.test.singleton(DummySource.SENTINEL, DummySource.SENTINEL)

    @inject(dependencies=[Get(Dummy, source=dummy_source)])
    def f(x):
        return x

    @inject
    def g(x: Annotated[Dummy, Get(Dummy, source=dummy_source)]):
        return x

    assert f() is DummySource.SENTINEL
    assert g() is DummySource.SENTINEL


def test_invalid_source():
    class Dummy:
        pass

    class DummySource:
        pass

    with pytest.raises(TypeError, match=".*source.*"):
        Get(Dummy, source=DummySource())


def test_invalid_factory():
    class Dummy:
        pass

    with pytest.raises(TypeError, match=".*factory.*"):
        Get(Dummy, source=object())

    with pytest.raises(ValueError, match="(?i).*factory.*declared.*"):
        Get(Dummy, source=Dummy)


def test_invalid_factory_output():
    class Dummy:
        pass

    class F:
        pass

    @factory
    def dummy_factory() -> Dummy:
        return Dummy()

    with pytest.raises(TypeError, match=".*dependency.*class"):
        Get(object(), source=dummy_factory)

    with pytest.raises(TypeError, match=".*dependency.*does not match.*factory.*"):
        Get(F, source=dummy_factory)
