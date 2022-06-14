import inspect
from typing import Any, TypeVar

import pytest

from antidote import inject, world
from tests.utils import Obj

T = TypeVar("T")
dep_x = Obj()


def wrap(f: T) -> T:
    return inject(kwargs=dict(x=dep_x))(f)  # type: ignore


def func_with_annotations(x: int) -> None:
    ...


def func_with_defaults(x: int, y: int = 3) -> None:
    ...


def func_with_kw_only(x: int, *, y: int) -> None:
    ...


wrapped_func_with_annotations = wrap(func_with_annotations)
wrapped_func_with_defaults = wrap(func_with_defaults)
wrapped_func_with_kw_only = wrap(func_with_kw_only)


async def async_func_with_annotations(x: int) -> None:
    ...


async def async_func_with_defaults(x: int, y: int = 3) -> None:
    ...


async def async_func_with_kw_only(x: int, *, y: int) -> None:
    ...


wrapped_async_func_with_annotations = wrap(async_func_with_annotations)
wrapped_async_func_with_defaults = wrap(async_func_with_defaults)
wrapped_async_func_with_kw_only = wrap(async_func_with_kw_only)


class Klass:
    def method_with_annotations(self, x: int) -> None:
        ...

    def method_with_defaults(self, x: int, y: int = 3) -> None:
        ...

    def method_with_kw_only(self, x: int, *, y: int) -> None:
        ...

    wrapped_method_with_annotations = wrap(method_with_annotations)
    wrapped_method_with_defaults = wrap(method_with_defaults)
    wrapped_method_with_kw_only = wrap(method_with_kw_only)

    @classmethod
    def cls_with_annotations(cls, x: int) -> None:
        ...

    @classmethod
    def cls_with_defaults(cls, x: int, y: int = 3) -> None:
        ...

    @classmethod
    def cls_with_kw_only(cls, x: int, *, y: int) -> None:
        ...

    wrapped_cls_with_annotations = wrap(cls_with_annotations)
    wrapped_cls_with_defaults = wrap(cls_with_defaults)
    wrapped_cls_with_kw_only = wrap(cls_with_kw_only)

    @staticmethod
    def static_with_annotations(x: int) -> None:
        ...

    @staticmethod
    def static_with_defaults(x: int, y: int = 3) -> None:
        ...

    @staticmethod
    def static_with_kw_only(x: int, *, y: int) -> None:
        ...

    wrapped_static_with_annotations = wrap(static_with_annotations)
    wrapped_static_with_defaults = wrap(static_with_defaults)
    wrapped_static_with_kw_only = wrap(static_with_kw_only)

    async def async_method_with_annotations(self, x: int) -> None:
        ...

    async def async_method_with_defaults(self, x: int, y: int = 3) -> None:
        ...

    async def async_method_with_kw_only(self, x: int, *, y: int) -> None:
        ...

    wrapped_async_method_with_annotations = wrap(async_method_with_annotations)
    wrapped_async_method_with_defaults = wrap(async_method_with_defaults)
    wrapped_async_method_with_kw_only = wrap(async_method_with_kw_only)

    @classmethod
    async def async_cls_with_annotations(cls, x: int) -> None:
        ...

    @classmethod
    async def async_cls_with_defaults(cls, x: int, y: int = 3) -> None:
        ...

    @classmethod
    async def async_cls_with_kw_only(cls, x: int, *, y: int) -> None:
        ...

    wrapped_async_cls_with_annotations = wrap(async_cls_with_annotations)
    wrapped_async_cls_with_defaults = wrap(async_cls_with_defaults)
    wrapped_async_cls_with_kw_only = wrap(async_cls_with_kw_only)

    @staticmethod
    async def async_static_with_annotations(x: int) -> None:
        ...

    @staticmethod
    async def async_static_with_defaults(x: int, y: int = 3) -> None:
        ...

    @staticmethod
    async def async_static_with_kw_only(x: int, *, y: int) -> None:
        ...

    wrapped_async_static_with_annotations = wrap(async_static_with_annotations)
    wrapped_async_static_with_defaults = wrap(async_static_with_defaults)
    wrapped_async_static_with_kw_only = wrap(async_static_with_kw_only)


instance = Klass()


@pytest.mark.parametrize(
    "original,wrapped,strict_is",
    [
        pytest.param(
            func_with_annotations, wrapped_func_with_annotations, True, id="func_with_annotations"
        ),
        pytest.param(func_with_defaults, wrapped_func_with_defaults, True, id="func_with_defaults"),
        pytest.param(func_with_kw_only, wrapped_func_with_kw_only, True, id="func_with_kw_only"),
        pytest.param(
            Klass.method_with_annotations,
            Klass.wrapped_method_with_annotations,
            True,
            id="Klass.method_with_annotations",
        ),
        pytest.param(
            Klass.method_with_defaults,
            Klass.wrapped_method_with_defaults,
            True,
            id="Klass.method_with_defaults",
        ),
        pytest.param(
            Klass.method_with_kw_only,
            Klass.wrapped_method_with_kw_only,
            True,
            id="Klass.method_with_kw_only",
        ),
        pytest.param(
            Klass.cls_with_annotations,
            Klass.wrapped_cls_with_annotations,
            False,
            id="Klass.cls_with_annotations",
        ),
        pytest.param(
            Klass.cls_with_defaults,
            Klass.wrapped_cls_with_defaults,
            False,
            id="Klass.cls_with_defaults",
        ),
        pytest.param(
            Klass.cls_with_kw_only,
            Klass.wrapped_cls_with_kw_only,
            False,
            id="Klass.cls_with_kw_only",
        ),
        pytest.param(
            Klass.static_with_annotations,
            Klass.wrapped_static_with_annotations,
            True,
            id="Klass.static_with_annotations",
        ),
        pytest.param(
            Klass.static_with_defaults,
            Klass.wrapped_static_with_defaults,
            True,
            id="Klass.static_with_defaults",
        ),
        pytest.param(
            Klass.static_with_kw_only,
            Klass.wrapped_static_with_kw_only,
            True,
            id="Klass.static_with_kw_only",
        ),
        pytest.param(
            instance.method_with_annotations,
            instance.wrapped_method_with_annotations,
            False,
            id="instance.method_with_annotations",
        ),
        pytest.param(
            instance.method_with_defaults,
            instance.wrapped_method_with_defaults,
            False,
            id="instance.method_with_defaults",
        ),
        pytest.param(
            instance.method_with_kw_only,
            instance.wrapped_method_with_kw_only,
            False,
            id="instance.method_with_kw_only",
        ),
        pytest.param(
            instance.cls_with_annotations,
            instance.wrapped_cls_with_annotations,  # type: ignore
            False,
            id="instance.cls_with_annotations",
        ),
        pytest.param(
            instance.cls_with_defaults,
            instance.wrapped_cls_with_defaults,  # type: ignore
            False,
            id="instance.cls_with_defaults",
        ),
        pytest.param(
            instance.cls_with_kw_only,
            instance.wrapped_cls_with_kw_only,  # type: ignore
            False,
            id="instance.cls_with_kw_only",
        ),
        pytest.param(
            instance.static_with_annotations,
            instance.wrapped_static_with_annotations,  # type: ignore
            True,
            id="instance.static_with_annotations",
        ),
        pytest.param(
            instance.static_with_defaults,
            instance.wrapped_static_with_defaults,  # type: ignore
            True,
            id="instance.static_with_defaults",
        ),
        pytest.param(
            instance.static_with_kw_only,
            instance.wrapped_static_with_kw_only,  # type: ignore
            True,
            id="instance.static_with_kw_only",
        ),
        pytest.param(
            Klass.async_method_with_annotations,
            Klass.wrapped_async_method_with_annotations,
            True,
            id="Klass.async_method_with_annotations",
        ),
        pytest.param(
            Klass.async_method_with_defaults,
            Klass.wrapped_async_method_with_defaults,
            True,
            id="Klass.async_method_with_defaults",
        ),
        pytest.param(
            Klass.async_method_with_kw_only,
            Klass.wrapped_async_method_with_kw_only,
            True,
            id="Klass.async_method_with_kw_only",
        ),
        pytest.param(
            Klass.async_cls_with_annotations,
            Klass.wrapped_async_cls_with_annotations,
            False,
            id="Klass.async_cls_with_annotations",
        ),
        pytest.param(
            Klass.async_cls_with_defaults,
            Klass.wrapped_async_cls_with_defaults,
            False,
            id="Klass.async_cls_with_defaults",
        ),
        pytest.param(
            Klass.async_cls_with_kw_only,
            Klass.wrapped_async_cls_with_kw_only,
            False,
            id="Klass.async_cls_with_kw_only",
        ),
        pytest.param(
            Klass.async_static_with_annotations,
            Klass.wrapped_async_static_with_annotations,
            True,
            id="Klass.async_static_with_annotations",
        ),
        pytest.param(
            Klass.async_static_with_defaults,
            Klass.wrapped_async_static_with_defaults,
            True,
            id="Klass.async_static_with_defaults",
        ),
        pytest.param(
            Klass.async_static_with_kw_only,
            Klass.wrapped_async_static_with_kw_only,
            True,
            id="Klass.async_static_with_kw_only",
        ),
        pytest.param(
            instance.async_method_with_annotations,
            instance.wrapped_async_method_with_annotations,
            False,
            id="instance.async_method_with_annotations",
        ),
        pytest.param(
            instance.async_method_with_defaults,
            instance.wrapped_async_method_with_defaults,
            False,
            id="instance.async_method_with_defaults",
        ),
        pytest.param(
            instance.async_method_with_kw_only,
            instance.wrapped_async_method_with_kw_only,
            False,
            id="instance.async_method_with_kw_only",
        ),
        pytest.param(
            instance.async_cls_with_annotations,
            instance.wrapped_async_cls_with_annotations,  # type: ignore
            False,
            id="instance.async_cls_with_annotations",
        ),
        pytest.param(
            instance.async_cls_with_defaults,
            instance.wrapped_async_cls_with_defaults,  # type: ignore
            False,
            id="instance.async_cls_with_defaults",
        ),
        pytest.param(
            instance.async_cls_with_kw_only,
            instance.wrapped_async_cls_with_kw_only,  # type: ignore
            False,
            id="instance.async_cls_with_kw_only",
        ),
        pytest.param(
            instance.async_static_with_annotations,
            instance.wrapped_async_static_with_annotations,  # type: ignore
            True,
            id="instance.async_static_with_annotations",
        ),
        pytest.param(
            instance.async_static_with_defaults,
            instance.wrapped_async_static_with_defaults,  # type: ignore
            True,
            id="instance.async_static_with_defaults",
        ),
        pytest.param(
            instance.async_static_with_kw_only,
            instance.wrapped_async_static_with_kw_only,  # type: ignore
            True,
            id="instance.async_static_with_kw_only",
        ),
    ],
)
def test_wrapped_attributes(original: Any, wrapped: Any, strict_is: Any) -> None:
    assert original.__name__ == wrapped.__name__, "__name__"
    assert original.__doc__ == wrapped.__doc__, "__doc__"
    assert original.__code__ == wrapped.__code__, "__code__"
    assert original.__defaults__ == wrapped.__defaults__, "__defaults__"
    assert original.__globals__ == wrapped.__globals__, "__globals__"
    assert original.__annotations__ == wrapped.__annotations__, "__annotations__"
    assert original.__kwdefaults__ == wrapped.__kwdefaults__, "__kwdefaults__"
    assert original.__module__ == wrapped.__module__, "__module__"
    assert original.__qualname__ == wrapped.__qualname__, "__qualname__"

    try:
        func = original.__func__
    except AttributeError:
        with pytest.raises(AttributeError):
            wrapped.__func__
        assert original is wrapped.__wrapped__
    else:
        # Either method or class/static-method
        assert original == wrapped.__wrapped__ or func is wrapped.__func__.__wrapped__

    try:
        assert original.__self__ is wrapped.__self__
    except AttributeError:
        with pytest.raises(AttributeError):
            wrapped.__self__

    assert inspect.signature(original) == inspect.signature(wrapped), "signature"
    assert inspect.isfunction(original) == inspect.isfunction(wrapped), "isfunction"
    assert inspect.ismethod(original) == inspect.ismethod(wrapped), "ismethod"
    assert inspect.iscoroutinefunction(original) == inspect.iscoroutinefunction(
        wrapped
    ), "iscoroutinefunction"
    assert inspect.iscoroutine(original) == inspect.iscoroutine(wrapped), "iscoroutine"
    assert repr(original) in repr(wrapped)
    assert str(original) == str(wrapped)


def test_static_class_method() -> None:
    with world.test.empty() as overrides:
        overrides[dep_x] = Obj()

        class Dummy:
            @wrap
            @classmethod
            def klass(cls, x: object = object()) -> object:
                return x

            @wrap
            @staticmethod
            def static(x: object = object()) -> object:
                return x

            # still class/static-method
            assert isinstance(klass, classmethod)
            assert isinstance(static, staticmethod)

        # was properly injected
        assert Dummy.klass() is world[dep_x]
        assert Dummy.static() is world[dep_x]


def test_attributes() -> None:
    a = Obj()
    b = Obj()

    def f(a: object) -> None:
        ...

    f.a = a  # type: ignore

    injected_f = inject(dict(a=a))(f)
    assert injected_f.a is a  # type: ignore

    injected_f.b = b  # type: ignore
    assert injected_f.b is b  # type: ignore

    assert injected_f.__wrapped__ is f  # type: ignore
