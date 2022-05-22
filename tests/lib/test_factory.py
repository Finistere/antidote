from contextlib import contextmanager
from typing import Any, Callable

import pytest

from antidote import Factory, factory, inject, Inject, Provide, Service, Wiring, world
from antidote.exceptions import DependencyInstantiationError


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(autouse=True)
def test_world():
    with world.test.new():
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


@pytest.fixture(params=["function", "class", "decorated_class"])
def build(test_world, request):
    if request.param == "function":

        @factory
        def build(**kwargs) -> A:
            return A(**kwargs)

        return build
    elif request.param == "class":

        class ServiceFactory(Factory):
            def __call__(self, **kwargs) -> A:
                return A(**kwargs)

        return ServiceFactory
    else:

        @factory
        class ServiceFactory:
            def __call__(self, **kwargs) -> A:
                return A(**kwargs)

        return ServiceFactory


def test_simple(build: Callable[..., A]):
    # working dependency
    assert isinstance(world.get(A, source=build), A)
    assert world.get(A, source=build) is world.get(A, source=build)


def test_pass_through(build):
    if isinstance(build, type):
        build = build()

    assert isinstance(build(), A)

    x = object()
    a = build(x=x)
    assert a.kwargs == dict(x=x)


def test_legacy_notation():
    @factory
    def f() -> A:
        return A()

    class BFactory(Factory):
        def __call__(self) -> B:
            return B()

    assert isinstance(world.get(A @ f), A)
    assert isinstance(world.get(B @ BFactory), B)


def test_custom_scope():
    dummy_scope = world.scopes.new(name="dummy")

    class Scoped:
        pass

    class ScopedF(Factory):
        __antidote__ = Factory.Conf(scope=dummy_scope)

        def __call__(self) -> Scoped:
            return Scoped()

    x = world.get(Scoped @ ScopedF)
    assert world.get(Scoped @ ScopedF) is x
    world.scopes.reset(dummy_scope)
    assert world.get(Scoped @ ScopedF) is not x

    @factory(scope=dummy_scope)
    def scoped_factory() -> Scoped:
        return Scoped()

    x = world.get(Scoped @ scoped_factory)
    assert world.get(Scoped @ scoped_factory) is x
    world.scopes.reset(dummy_scope)
    assert world.get(Scoped @ scoped_factory) is not x


def test_parameterized():
    x = object()

    class BuildA(Factory):
        __antidote__ = Factory.Conf(parameters=["x"])

        def __call__(self, **kwargs) -> A:
            return A(**kwargs)

    a = world.get(A @ BuildA.parameterized(x=x))
    assert a.kwargs == dict(x=x)

    with pytest.raises(ValueError, match=".*parameters.*'x'.*"):
        A @ BuildA.parameterized()

    with pytest.raises(ValueError, match=".*parameters.*'x'.*"):
        A @ BuildA.parameterized(unknown="something")


def test_not_parametrized():
    class BuildA(Factory):
        def __call__(self) -> A:
            return A()

    with pytest.raises(RuntimeError, match=".*parameters.*"):
        B @ BuildA.parameterized(x=1)


def test_invalid_with_default_parameters():
    with pytest.raises(ValueError, match=".*default.*"):

        class BuildA(Factory):
            __antidote__ = Factory.Conf(parameters=["x"])

            def __call__(self, x: str = "default") -> A:
                return A()


def test_invalid_with_injected_parameters():
    class Dummy(Service):
        pass

    with pytest.raises(ValueError, match=".*injected.*class.*Dummy.*"):

        class BuildA(Factory):
            __antidote__ = Factory.Conf(parameters=["x"])

            def __call__(self, x: Provide[Dummy]) -> A:
                return A()


def test_invalid_parameterized_dependency():
    class BuildA(Factory):
        __antidote__ = Factory.Conf(parameters=["x"])

        def __call__(self, x) -> A:
            return A()

    with pytest.raises(ValueError, match="Unsupported output.*"):
        B @ BuildA.parameterized(x=1)


def test_invalid_dependency():
    @factory
    def f() -> A:
        pass

    with pytest.raises(ValueError, match="Unsupported output.*"):
        B @ f

    class F(Factory):
        def __call__(self) -> A:
            pass

    with pytest.raises(ValueError, match="Unsupported output.*"):
        B @ F


def test_getattr():
    def build() -> A:
        return A()

    build.hello = "world"

    build = factory(build)
    assert build.hello == "world"

    build.new_hello = "new_world"
    assert build.new_hello == "new_world"


def test_wiring():
    world.test.singleton(A, A())

    @factory
    def build_b(a: A = inject.me()) -> B:
        return B()

    @factory
    class BuildB:
        def __call__(self, a: A = inject.me()) -> B:
            return B()

    assert isinstance(world.get(B, source=build_b), B)
    assert isinstance(world.get(B, source=BuildB), B)


def test_wiring_none():
    world.test.singleton(A, A())

    @factory(wiring=None)
    def build_b2(a: Inject[A]) -> B:
        return B()

    @factory(wiring=None)
    class BuildB2:
        def __call__(self, a: Inject[A]) -> B:
            return B()

    with pytest.raises(DependencyInstantiationError):
        world.get(B, source=build_b2)

    with pytest.raises(TypeError):
        build_b2()

    with pytest.raises(DependencyInstantiationError):
        world.get(B, source=BuildB2)

    with pytest.raises(TypeError):
        BuildB2()()


def test_wiring_custom():
    world.test.singleton(B, B())

    @factory(wiring=Wiring(dependencies=dict(b=B)))
    def build_b3(b) -> B:
        return b

    @factory(wiring=Wiring(dependencies=dict(b=B)))
    class BuildB3:
        def __call__(self, b) -> B:
            return b

    assert world.get(B, source=build_b3) is world.get(B)
    assert world.get(B, source=BuildB3) is world.get(B)


def test_missing_call():
    with pytest.raises(TypeError, match="__call__"):

        class ServiceFactory(Factory):
            pass

    with pytest.raises(ValueError, match=".*return type hint.*"):

        @factory
        class ServiceFactory2:
            pass


def test_missing_return_type_hint():
    with pytest.raises(ValueError, match=".*return type hint.*"):

        @factory
        def faulty_service_provider():
            return A()

    with pytest.raises(TypeError, match=".*return type hint.*"):

        @factory
        def faulty_service_provider2() -> Any:
            return A()

    with pytest.raises(ValueError, match=".*return type hint.*"):

        @factory
        class FaultyServiceFactory:
            def __call__(self):
                return A()

    with pytest.raises(TypeError, match=".*return type hint.*"):

        @factory
        class FaultyServiceFactory2:
            def __call__(self) -> Any:
                return A()

    with pytest.raises(ValueError, match=".*return type hint.*"):

        class FaultyServiceFactory3(Factory):
            def __call__(self):
                return A()

    with pytest.raises(TypeError, match=".*return type hint.*"):

        class FaultyServiceFactory4(Factory):
            def __call__(self) -> Any:
                return A()


@pytest.mark.parametrize(
    "expectation,kwargs,func",
    [
        pytest.param(
            pytest.raises(TypeError, match=".*function.*"), dict(), object(), id="function"
        ),
        pytest.param(
            pytest.raises(TypeError, match=".*singleton.*"),
            dict(singleton=object()),
            lambda: None,
            id="singleton",
        ),
        pytest.param(
            pytest.raises(TypeError, match=".*scope.*"),
            dict(scope=object()),
            lambda: None,
            id="scope",
        ),
        pytest.param(
            pytest.raises(TypeError, match=".*wiring.*"),
            dict(wiring=object()),
            lambda: None,
            id="wiring",
        ),
    ],
)
def test_invalid_factory_args(expectation, kwargs: dict, func: Callable[..., object]):
    with expectation:
        factory(**kwargs)(func)

    with expectation:
        factory(func, **kwargs)


def test_no_subclass_of_service():
    class Dummy(Factory):
        def __call__(self, *args, **kwargs) -> A:
            pass

    with pytest.raises(TypeError, match=".*abstract.*"):

        class SubDummy(Dummy):
            def __call__(self, *args, **kwargs) -> B:
                pass


def test_invalid_conf():
    with pytest.raises(TypeError, match=".*__antidote__.*"):

        class Dummy(Factory):
            __antidote__ = object()

            def __call__(self) -> A:
                pass


@pytest.mark.parametrize(
    "expectation, parameters",
    [
        (pytest.raises(TypeError), "string"),
        (pytest.raises(TypeError), object()),
        (pytest.raises(TypeError), [1]),
        (does_not_raise(), ["x"]),
        (does_not_raise(), []),
        (does_not_raise(), None),
    ],
)
def test_conf_parameters(expectation, parameters):
    with expectation:

        class Build(Factory):
            __antidote__ = Factory.Conf(parameters=parameters)

            def __call__(self, *args, **kwargs) -> A:
                pass


@pytest.mark.parametrize(
    "expectation, kwargs",
    [
        pytest.param(pytest.raises(TypeError, match=f".*{arg}.*"), {arg: object()}, id=arg)
        for arg in ["wiring", "singleton", "scope", "parameters"]
    ],
)
def test_invalid_conf_args(kwargs, expectation):
    with expectation:
        Factory.Conf(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(singleton=False),
        dict(scope=None),
        dict(wiring=Wiring(methods=["method"])),
        dict(parameters=frozenset(["x"])),
    ],
)
def test_conf_copy(kwargs):
    conf = Factory.Conf(singleton=True).copy(**kwargs)
    for k, v in kwargs.items():
        assert getattr(conf, k) == v


def test_invalid_copy():
    conf = Factory.Conf()
    with pytest.raises(TypeError, match=".*both.*"):
        conf.copy(singleton=False, scope=None)


def test_conf_repr():
    conf = Factory.Conf()
    assert "scope" in repr(conf)


def test_default_injection():
    class MyService(Service):
        pass

    class A:
        pass

    injected = None

    @factory
    def build_a(s: Provide[MyService]) -> A:
        nonlocal injected
        injected = s
        return A()

    assert isinstance(world.get(A @ build_a), A)
    assert injected is world.get(MyService)


def test_double_injection():
    world.test.singleton(B, object())

    injected = None

    @factory
    @inject(auto_provide=True)
    def build_a(s: B) -> A:
        nonlocal injected
        injected = s
        return A()

    assert isinstance(world.get(A @ build_a), A)
    assert injected is world.get(B)
