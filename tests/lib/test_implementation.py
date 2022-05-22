import pytest

from antidote import Factory, factory, implementation, inject, Provide, injectable, Service, world
from antidote._implementation import validate_provided_class
from antidote.exceptions import DependencyInstantiationError


@pytest.fixture(autouse=True)
def test_world():
    with world.test.new():
        yield


class Interface:
    pass


def test_default_implementation():
    class A(Interface, Service):
        pass

    class B(Interface, Service):
        pass

    choice = "a"

    @implementation(Interface)
    def choose():
        return dict(a=A, b=B)[choice]

    assert world.get(Interface @ choose) is world.get(A)
    choice = "b"
    assert choose() is B
    assert world.get(Interface @ choose) is world.get(A)


@pytest.mark.parametrize(
    "singleton,permanent", [(True, True), (True, False), (False, True), (False, False)]
)
def test_implementation(singleton: bool, permanent: bool):
    choice = "a"

    class A(Interface, Service):
        __antidote__ = Service.Conf(singleton=singleton)

    class B(Interface, Service):
        __antidote__ = Service.Conf(singleton=singleton)

    @implementation(Interface, permanent=permanent)
    def choose_service():
        return dict(a=A, b=B)[choice]

    dependency = Interface @ choose_service
    assert isinstance(world.get(dependency), A)
    assert (world.get(dependency) is world.get(A)) is singleton

    choice = "b"
    assert choose_service() == B
    if permanent:
        assert isinstance(world.get(dependency), A)
        assert (world.get(dependency) is world.get(A)) is singleton
    else:
        assert isinstance(world.get(dependency), B)
        assert (world.get(dependency) is world.get(B)) is singleton


def test_implementation_parameterized_service():
    x = object()

    class A(Interface, Service):
        __antidote__ = Service.Conf(parameters=["test"])

        def __init__(self, **kwargs):
            self.kwargs = kwargs

    @implementation(Interface)
    def impl():
        return A.parameterized(test=x)

    a = world.get(Interface @ impl)
    assert isinstance(a, A)
    assert a.kwargs == dict(test=x)


def test_implementation_with_factory():
    x = object()

    class A(Interface):
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class BuildA(Factory):
        __antidote__ = Factory.Conf(parameters=["test"])

        def __call__(self, **kwargs) -> A:
            return A(**kwargs)

    @implementation(Interface)
    def impl2():
        return A @ BuildA.parameterized(test=x)

    a = world.get(Interface @ impl2)
    assert isinstance(a, A)
    assert a.kwargs == dict(test=x)


def dummy_choose():
    class A(Interface):
        pass

    return A


@pytest.mark.parametrize(
    "expectation,kwargs,func",
    [
        pytest.param(
            pytest.raises(TypeError, match=".*function.*"),
            dict(interface=Interface),
            object(),
            id="function",
        ),
        pytest.param(
            pytest.raises(TypeError, match=".*interface.*"),
            dict(interface=object()),
            dummy_choose,
            id="interface",
        ),
        pytest.param(
            pytest.raises(TypeError, match=".*permanent.*"),
            {"interface": Interface, "permanent": object()},
            dummy_choose,
            id="permanent",
        ),
    ],
)
def test_invalid_implementation(expectation, kwargs: dict, func):
    with expectation:
        implementation(**kwargs)(func)


def test_invalid_implementation_return_type():
    class B:
        pass

    world.test.singleton(B, 1)

    with world.test.new():
        world.test.singleton(1, 1)

        @implementation(Interface)
        def choose():
            return 1

        world.get(1)
        with pytest.raises(DependencyInstantiationError):
            world.get(Interface @ choose)

    with world.test.new():
        world.test.singleton(B, 1)

        @implementation(Interface)
        def choose2():
            return B

        world.get(B)
        with pytest.raises(DependencyInstantiationError):
            world.get(Interface @ choose2)

    with world.test.new():

        class C(Service):
            __antidote__ = Service.Conf(parameters=["test"])

            def __init__(self, **kwargs):
                self.kwargs = kwargs

        @implementation(Interface)
        def impl():
            return C.parameterized(test=1)

        world.get(C.parameterized(test=1))
        with pytest.raises(DependencyInstantiationError):
            world.get(Interface @ impl)

    with world.test.new():

        class D:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class BuildD(Factory):
            __antidote__ = Factory.Conf(parameters=["test"])

            def __call__(self, **kwargs) -> D:
                return D(**kwargs)

        @implementation(Interface)
        def impl2():
            return D @ BuildD.parameterized(test=1)

        world.get(D @ BuildD.parameterized(test=1))
        with pytest.raises(DependencyInstantiationError):
            world.get(Interface @ impl2)


def test_invalid_implementation_dependency():
    class Interface:
        pass

    class A(Interface, Service):
        pass

    @implementation(Interface)
    def current_interface():
        return A

    with pytest.raises(ValueError, match=".*interface.*"):
        A @ current_interface


def test_getattr():
    class Interface:
        pass

    class A(Interface, Service):
        pass

    def current_interface():
        return A

    current_interface.hello = "world"

    build = implementation(Interface)(current_interface)
    assert build.hello == "world"

    build.new_hello = "new_world"
    assert build.new_hello == "new_world"


def test_validate_provided_class():
    class Interface:
        pass

    with pytest.raises(TypeError):
        validate_provided_class(object(), expected=Interface)

    class A(Interface, Service):
        __antidote__ = Service.Conf(parameters=["a"])

    class B(Service):
        __antidote__ = Service.Conf(parameters=["a"])

    validate_provided_class(A, expected=Interface)
    validate_provided_class(B, expected=B)
    with pytest.raises(TypeError):
        validate_provided_class(B, expected=Interface)

    validate_provided_class(A.parameterized(a=1), expected=Interface)
    validate_provided_class(B.parameterized(a=1), expected=B)
    with pytest.raises(TypeError):
        validate_provided_class(B.parameterized(a=1), expected=Interface)

    @implementation(Interface)
    def choose_a():
        return A

    @implementation(B)
    def choose_b():
        return B

    validate_provided_class(Interface @ choose_a, expected=Interface)
    validate_provided_class(B @ choose_b, expected=B)
    with pytest.raises(TypeError):
        validate_provided_class(B @ choose_b, expected=Interface)


def test_validate_provided_class_factory():
    class Interface:
        pass

    class A(Interface):
        pass

    class B:
        pass

    with world.test.new():

        @factory
        def build_a() -> A:
            return A()

        @factory
        def build_b() -> B:
            return B()

        validate_provided_class(A @ build_a, expected=Interface)
        validate_provided_class(B @ build_b, expected=B)
        with pytest.raises(TypeError):
            validate_provided_class(B @ build_b, expected=Interface)

    with world.test.new():

        class BuildA(Factory):
            __antidote__ = Factory.Conf(parameters=["a"])

            def __call__(self, **kwargs) -> A:
                return A(**kwargs)

        class BuildB(Factory):
            __antidote__ = Factory.Conf(parameters=["a"])

            def __call__(self, **kwargs) -> B:
                return B(**kwargs)

        validate_provided_class(A @ BuildA, expected=Interface)
        validate_provided_class(B @ BuildB, expected=B)
        with pytest.raises(TypeError):
            validate_provided_class(B @ BuildB, expected=Interface)

        validate_provided_class(A @ BuildA.parameterized(a=1), expected=Interface)
        validate_provided_class(B @ BuildB.parameterized(a=1), expected=B)
        with pytest.raises(TypeError):
            validate_provided_class(B @ BuildB.parameterized(a=1), expected=Interface)


def test_default_injection():
    class MyService(Service):
        pass

    class Interface:
        pass

    class A(Interface, Service):
        pass

    injected = None

    @implementation(Interface)
    def choose_a(s: Provide[MyService]):
        nonlocal injected
        injected = s
        return A

    assert world.get(Interface @ choose_a) is world.get(A)
    assert injected is world.get(MyService)


def test_double_injection():
    class B:
        pass

    world.test.singleton(B, object())

    class Interface:
        pass

    class A(Interface, Service):
        pass

    injected = None

    @implementation(Interface)
    @inject(auto_provide=True)
    def choose_a(s: B):
        nonlocal injected
        injected = s
        return A

    assert world.get(Interface @ choose_a) is world.get(A)
    assert injected is world.get(B)


def test_source_notation():
    @injectable
    class A(Interface):
        pass

    @implementation(Interface)
    def choose():
        return A

    assert world.get(Interface, source=choose) is world.get(A)

    @inject
    def f(a: Interface = inject.me(source=choose)) -> Interface:
        return a

    assert f() is world.get(A)

    with pytest.raises(ValueError, match="Unsupported interface.*"):
        world.get(A, source=choose)
