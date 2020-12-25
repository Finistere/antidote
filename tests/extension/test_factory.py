from typing import Any, Type

import pytest

from antidote import Factory, factory, Tag, Wiring, world
from antidote._providers import (FactoryProvider, LazyProvider, ServiceProvider,
                                 TagProvider)


@pytest.fixture(autouse=True)
def test_world():
    with world.test.empty():
        world.provider(ServiceProvider)
        world.provider(FactoryProvider)
        world.provider(LazyProvider)
        world.provider(TagProvider)
        yield


class A:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class B:
    pass


class C:
    pass


def dummy() -> A:
    pass


@pytest.fixture(params=['function', 'class'])
def build(test_world, request):
    if request.param == 'function':
        @factory
        def build(**kwargs) -> A:
            return A(**kwargs)

        return build
    else:
        class ServiceFactory(Factory):
            def __call__(self, **kwargs) -> A:
                return A(**kwargs)

        return ServiceFactory


def test_simple(build: Type[Factory]):
    # working dependency
    assert isinstance(world.get(A @ build), A)
    assert world.get(A @ build) is world.get(A @ build)


def test_pass_through(build):
    if isinstance(build, type) and issubclass(build, Factory):
        build = build()

    assert isinstance(build(), A)

    x = object()
    a = build(x=x)
    assert a.kwargs == dict(x=x)


def test_auto_wire():
    world.singletons.add(C, C())

    with world.test.clone(keep_singletons=True):
        @factory
        def build(x: C = None) -> A:
            return x

        assert world.get(A @ build) is world.get(C)

    with world.test.clone(keep_singletons=True):
        @factory(auto_wire=True)
        def build(x: C = None) -> A:
            return x

        assert world.get(A @ build) is world.get(C)

    with world.test.clone(keep_singletons=True):
        @factory(auto_wire=False)
        def build(x: C = None) -> A:
            return x

        assert world.get(A @ build) is None


def test_tags():
    tag = Tag()
    with world.test.clone():
        @factory(tags=[tag])
        def build() -> A:
            return A()

        a = next(world.get(tag).values())
        assert isinstance(a, A)
        assert a is world.get(A @ build)

    with world.test.clone():
        class ServiceFactory(Factory):
            __antidote__ = Factory.Conf(tags=[tag])

            def __call__(self) -> A:
                return A()

        a = next(world.get(tag).values())
        assert isinstance(a, A)
        assert a is world.get(A @ ServiceFactory)

    with world.test.empty():
        world.provider(FactoryProvider)

        with pytest.raises(RuntimeError):
            @factory(tags=[tag])
            def build() -> A:
                return A()

    with world.test.empty():
        world.provider(FactoryProvider)

        with pytest.raises(RuntimeError):
            class ServiceFactory(Factory):
                __antidote__ = Factory.Conf(tags=[tag])

                def __call__(self) -> A:
                    return A()


def test_with_kwargs(build: Type[Factory]):
    x = object()
    a = world.get(A @ build.with_kwargs(x=x))
    assert a.kwargs == dict(x=x)

    with pytest.raises(ValueError, match=".*with_kwargs.*"):
        A @ build.with_kwargs()


def test_getattr():
    def build() -> A:
        return A()

    build.hello = 'world'

    build = factory(build)
    assert build.hello == 'world'

    build.new_hello = 'new_world'
    assert build.new_hello == 'new_world'


def test_invalid_dependency(build: Type[Factory]):
    with pytest.raises(ValueError, match="Unsupported output.*"):
        B @ build

    with pytest.raises(ValueError, match="Unsupported output.*"):
        B @ build.with_kwargs(x=1)


def test_invalid_conf():
    with pytest.raises(TypeError, match=".*__antidote__.*"):
        class Dummy(Factory):
            __antidote__ = 1

            def __call__(self) -> A:
                pass


def test_missing_call():
    with pytest.raises(TypeError, match="__call__"):
        class ServiceFactory(Factory):
            pass


def test_missing_return_type_hint():
    with pytest.raises(ValueError):
        @factory
        def faulty_service_provider():
            return A()

    with pytest.raises(TypeError):
        @factory
        def faulty_service_provider2() -> Any:
            return A()

    with pytest.raises(ValueError):
        class FaultyServiceFactory(Factory):
            def __call__(self):
                return A()

    with pytest.raises(TypeError):
        class FaultyServiceFactory2(Factory):
            def __call__(self) -> Any:
                return A()


@pytest.mark.parametrize('kwargs, expectation', [
    (dict(f=1), pytest.raises(TypeError, match=".*function.*")),
    (dict(f=dummy, auto_wire=1), pytest.raises(TypeError, match=".*auto_wire.*")),
])
def test_invalid_args(kwargs, expectation):
    with expectation:
        factory(kwargs.pop('f'), **kwargs)


def test_no_subclass_of_service():
    class Dummy(Factory):
        def __call__(self, *args, **kwargs) -> A:
            pass

    with pytest.raises(TypeError, match=".*abstract.*"):
        class SubDummy(Dummy):
            def __call__(self, *args, **kwargs) -> B:
                pass


@pytest.mark.parametrize('kwargs, expectation', [
    (dict(public=object()), pytest.raises(TypeError, match=".*public.*")),
    (dict(singleton=object()), pytest.raises(TypeError, match=".*singleton.*")),
    (dict(tags=object()), pytest.raises(TypeError, match=".*tags.*")),
    (dict(tags=['dummy']), pytest.raises(TypeError, match=".*tags.*")),
    (dict(wiring=object()), pytest.raises(TypeError, match=".*wiring.*")),
])
def test_conf_error(kwargs, expectation):
    with expectation:
        Factory.Conf(**kwargs)


@pytest.mark.parametrize('kwargs', [
    dict(singleton=False),
    dict(tags=(Tag(),)),
    dict(public=True),
    dict(wiring=Wiring(methods=['method'])),
])
def test_conf_copy(kwargs):
    conf = Factory.Conf(singleton=True, tags=[], public=False).copy(**kwargs)
    for k, v in kwargs.items():
        assert getattr(conf, k) == v
