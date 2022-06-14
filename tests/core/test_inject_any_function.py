from __future__ import annotations

import functools
from typing import Any, Callable, cast, Tuple

import pytest
from typing_extensions import Protocol, TypeAlias

from antidote.core import DependencyNotFoundError, DoubleInjectionError, inject, world
from tests.utils import Obj


class A(Obj):
    ...


class B(Obj):
    ...


default_b = B()
a = A()
b = B()
dep_a = Obj()
dep_b = Obj()
dep_a_value = A()
dep_b_value = B()
unknown_a = A()
unknown_b = B()


class Func(Protocol):
    def __call__(self, a: A, *, b: B = default_b) -> Tuple[A, B]:
        ...


class AsyncFunc(Protocol):
    async def __call__(self, a: A, *, b: B = default_b) -> Tuple[A, B]:
        ...


CreateFunc: TypeAlias = Callable[[Callable[[Any], Any]], Func]
CreateAsyncFunc: TypeAlias = Callable[[Callable[[Any], Any]], AsyncFunc]


@pytest.fixture(
    params=[
        "function",
        "method",
        "classmethod_before",
        "classmethod_after",
        "staticmethod_before",
        "staticmethod_after",
        "instance_method",
        "instance_classmethod_before",
        "instance_classmethod_after",
        "instance_staticmethod_before",
        "instance_staticmethod_after",
    ]
)
def create(request: Any) -> CreateFunc:
    def callback(decorator: Callable[[Any], Any]) -> Any:
        if request.param == "function":

            @decorator
            def func(a: A, *, b: B = default_b) -> Tuple[A, B]:
                return a, b

            return func
        elif "classmethod_before" in request.param:

            class Klass:
                @classmethod
                @decorator
                def method(cls, a: A, *, b: B = default_b) -> Tuple[A, B]:
                    return a, b

            return Klass().method if "instance" in request.param else Klass.method
        elif "classmethod_after" in request.param:

            class Klass2:
                @decorator
                @classmethod
                def method(cls, a: A, *, b: B = default_b) -> Tuple[A, B]:
                    return a, b

            return Klass2().method if "instance" in request.param else Klass2.method
        elif "staticmethod_before" in request.param:

            class Klass3:
                @decorator
                @staticmethod
                def method(a: A, *, b: B = default_b) -> Tuple[A, B]:
                    return a, b

            return Klass3().method if "instance" in request.param else Klass3.method
        elif "staticmethod_after" in request.param:

            class Klass4:
                @staticmethod
                @decorator
                def method(a: A, *, b: B = default_b) -> Tuple[A, B]:
                    return a, b

            return Klass4().method if "instance" in request.param else Klass4.method
        elif "method" in request.param:

            class Klass5:
                @decorator
                def method(self, a: A, *, b: B = default_b) -> Tuple[A, B]:
                    return a, b

            if "instance" in request.param:
                return Klass5().method
            else:

                @functools.wraps(Klass5.method)
                def f(*args: Any, **kwargs: Any) -> Tuple[A, B]:
                    return Klass5.method(Klass5(), *args, **kwargs)  # type: ignore

                return f
        else:
            raise RuntimeError()  # pragma: no cover

    return cast(CreateFunc, callback)


@pytest.fixture(
    params=[
        "function",
        "method",
        "classmethod_before",
        "classmethod_after",
        "staticmethod_before",
        "staticmethod_after",
        "instance_method",
        "instance_classmethod_before",
        "instance_classmethod_after",
        "instance_staticmethod_before",
        "instance_staticmethod_after",
    ]
)
def create_async(request: Any) -> CreateFunc:
    def callback(decorator: Callable[[Any], Any]) -> Any:
        if request.param == "function":

            @decorator
            async def func(a: A, *, b: B = default_b) -> Tuple[A, B]:
                return a, b

            return func
        elif "classmethod_before" in request.param:

            class Klass:
                @classmethod
                @decorator
                async def method(cls, a: A, *, b: B = default_b) -> Tuple[A, B]:
                    return a, b

            return Klass().method if "instance" in request.param else Klass.method
        elif "classmethod_after" in request.param:

            class Klass2:
                @decorator
                @classmethod
                async def method(cls, a: A, *, b: B = default_b) -> Tuple[A, B]:
                    return a, b

            return Klass2().method if "instance" in request.param else Klass2.method
        elif "staticmethod_before" in request.param:

            class Klass3:
                @decorator
                @staticmethod
                async def method(a: A, *, b: B = default_b) -> Tuple[A, B]:
                    return a, b

            return Klass3().method if "instance" in request.param else Klass3.method
        elif "staticmethod_after" in request.param:

            class Klass4:
                @staticmethod
                @decorator
                async def method(a: A, *, b: B = default_b) -> Tuple[A, B]:
                    return a, b

            return Klass4().method if "instance" in request.param else Klass4.method
        elif "method" in request.param:

            class Klass5:
                @decorator
                async def method(self, a: A, *, b: B = default_b) -> Tuple[A, B]:
                    return a, b

            if "instance" in request.param:
                return Klass5().method
            else:

                @functools.wraps(Klass5.method)
                async def f(*args: Any, **kwargs: Any) -> Tuple[A, B]:
                    return await Klass5.method(Klass5(), *args, **kwargs)  # type: ignore

                return f
        else:
            raise RuntimeError()  # pragma: no cover

    return cast(CreateFunc, callback)


def test_no_injections(create: CreateFunc) -> None:
    func = create(inject)

    assert func(a, b=b) == (a, b)
    assert func(a) == (a, default_b)
    assert func(a, b=b) == (a, b)
    assert func(a=a, b=b) == (a, b)

    with pytest.raises(TypeError):
        func()  # type: ignore


async def test_async_no_injections(create_async: CreateAsyncFunc) -> None:
    func = create_async(inject)

    assert (await func(a, b=b)) == (a, b)
    assert (await func(a)) == (a, default_b)
    assert (await func(a, b=b)) == (a, b)
    assert (await func(a=a, b=b)) == (a, b)

    with pytest.raises(TypeError):
        await func()  # type: ignore


def test_double_injections(create: CreateFunc) -> None:
    func = create(inject(kwargs=dict(a=dep_a)))
    with pytest.raises(DoubleInjectionError):
        inject(func)


async def test_async_double_injections(create_async: CreateAsyncFunc) -> None:
    func = create_async(inject(kwargs=dict(a=dep_a)))
    with pytest.raises(DoubleInjectionError):
        inject(func)


kwargs_injections_test_cases = [
    pytest.param(dict(b=dep_b), (None, dep_b_value), id="_,dep_b"),
    pytest.param(dict(a=dep_a), (dep_a_value, None), id="dep_a,_"),
    pytest.param(dict(a=dep_a, b=dep_b), (dep_a_value, dep_b_value), id="dep_a,dep_b"),
    pytest.param(dict(a=unknown_a), (None, None), id="unknown_a,_"),
    pytest.param(dict(b=unknown_b), (None, None), id="_,unknown_b"),
    pytest.param(dict(a=unknown_a, b=unknown_b), (None, None), id="unknown_a,unknown_b"),
    pytest.param(dict(a=dep_a, b=unknown_b), (dep_a_value, None), id="dep_a,unknown_b"),
    pytest.param(dict(a=unknown_a, b=dep_b), (None, dep_b_value), id="unknown_a,dep_b"),
]


@pytest.mark.parametrize("kwargs, expected", kwargs_injections_test_cases)
def test_kwargs_injections(
    create: CreateFunc, kwargs: dict[str, object], expected: Tuple[object, object]
) -> None:
    with world.test.empty() as overrides:
        overrides.update({dep_a: dep_a_value, dep_b: dep_b_value})
        func = create(inject(kwargs=kwargs))
        expected_a, expected_b = expected
        expected_b = expected_b or default_b

        assert func(a, b=b) == (a, b)
        assert func(a, b=b) == (a, b)
        assert func(a=a, b=b) == (a, b)

        # b override
        assert func(a) == (a, expected_b)

        # a override
        if "a" in kwargs:
            if expected_a is not None:
                assert func() == (expected_a, expected_b)  # type: ignore
                assert func(b=b) == (expected_a, b)  # type: ignore
            else:
                with pytest.raises(DependencyNotFoundError):
                    func()  # type: ignore
        else:
            with pytest.raises(TypeError):
                func()  # type: ignore


@pytest.mark.parametrize("kwargs, expected", kwargs_injections_test_cases)
async def test_async_kwargs_injections(
    create_async: CreateAsyncFunc, kwargs: dict[str, object], expected: Tuple[object, object]
) -> None:
    with world.test.empty() as overrides:
        overrides.update({dep_a: dep_a_value, dep_b: dep_b_value})
        func = create_async(inject(kwargs=kwargs))
        expected_a, expected_b = expected
        expected_b = expected_b or default_b

        assert (await func(a, b=b)) == (a, b)
        assert (await func(a, b=b)) == (a, b)
        assert (await func(a=a, b=b)) == (a, b)

        # b override
        assert (await func(a)) == (a, expected_b)

        # a override
        if "a" in kwargs:
            if expected_a is not None:
                assert (await func()) == (expected_a, expected_b)  # type: ignore
                assert (await func(b=b)) == (expected_a, b)  # type: ignore
            else:
                with pytest.raises(DependencyNotFoundError):
                    await func()  # type: ignore
        else:
            with pytest.raises(TypeError):
                await func()  # type: ignore
