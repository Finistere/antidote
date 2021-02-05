import pytest

from antidote import LazyCall, LazyMethodCall, Service, world
from antidote._providers import LazyProvider, ServiceProvider


@pytest.fixture(autouse=True)
def empty_world():
    with world.test.empty():
        world.provider(LazyProvider)
        world.provider(ServiceProvider)
        yield


def test_lazy_singleton():
    def func():
        return object()

    test = LazyCall(func, singleton=False)
    assert world.get(test) != world.get(test)

    test2 = LazyCall(func, singleton=True)
    assert world.get(test2) is world.get(test2)

    default = LazyCall(func)
    assert world.get(default) is world.get(default)


@pytest.mark.parametrize(
    'args,kwargs',
    [
        ((1,), dict(test=2)),
        ((), dict(x=32)),
        ((4,), {})
    ]
)
def test_args_kwargs(args, kwargs):
    def func(*args_, **kwargs_):
        return args_, kwargs_

    test = LazyCall(func)(*args, **kwargs)
    assert (args, kwargs) == world.get(test)


def test_method_call():
    x = object()

    class Test(Service):
        def get(self, s):
            return s

        A = LazyMethodCall(get)(x)

    assert world.get(Test.A) is x


def test_method_same_instance():
    class Test(Service):
        def get(self):
            return self

        A = LazyMethodCall(get, singleton=True)
        B = LazyMethodCall(get, singleton=False)

    instance = world.get(Test)
    assert world.get(Test.A) is instance
    assert world.get(Test.B) is instance


def test_method_singleton():
    class Test(Service):
        def get(self):
            return object()

        A = LazyMethodCall(get, singleton=True)
        B = LazyMethodCall(get, singleton=False)
        C = LazyMethodCall(get)

    assert world.get(Test.A) is world.get(Test.A)
    assert world.get(Test.B) != world.get(Test.B)
    assert world.get(Test.C) is world.get(Test.C)  # singleton by default


def test_method_direct_call():
    class Test(Service):
        def get(self):
            return "Hello"

        A = LazyMethodCall(get)

    t = Test()
    assert t.A == "Hello"


@pytest.mark.parametrize(
    'args,kwargs',
    [
        ((1,), dict(test=2)),
        ((), dict(x=32)),
        ((4,), {})
    ]
)
def test_method_args_kwargs(args, kwargs):
    class Test(Service):
        def get(self, *args_, **kwargs_):
            return args_, kwargs_

        A = LazyMethodCall(get)(*args, **kwargs)

    assert (args, kwargs) == Test().A
    assert (args, kwargs) == world.get(Test.A)


def test_invalid_lazy_call():
    with pytest.raises(TypeError, match=".*func.*"):
        LazyCall(func=object())

    with pytest.raises(TypeError, match=".*singleton.*"):
        LazyCall(func=lambda: None, singleton=object())


def test_invalid_lazy_method_call():
    with pytest.raises(TypeError, match=".*method.*"):
        LazyMethodCall(method=object())

    with pytest.raises(TypeError, match=".*singleton.*"):
        LazyMethodCall(method=lambda: None, singleton=object())


def test_invalid_lazy_method_class():
    class Dummy:
        def get(self, x):
            pass

        A = LazyMethodCall(get)
        B = LazyMethodCall(get)(x=1)

    with pytest.raises(RuntimeError):
        Dummy.A

    with pytest.raises(RuntimeError):
        Dummy().A

    with pytest.raises(RuntimeError):
        Dummy.B

    with pytest.raises(RuntimeError):
        Dummy().B
