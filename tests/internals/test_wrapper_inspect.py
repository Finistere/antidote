import inspect

import pytest

from .test_wrapper import Opt, Required, wrap


def func():
    pass


def func_with_annotations(x: int):
    pass


def func_with_defaults(x, y=3):
    pass


def func_with_kw_only(x, *, y):
    pass


wrapped_func = wrap(func)
wrapped_func_with_annotations = wrap(x=Required())(func_with_annotations)
wrapped_func_with_defaults = wrap(x=Required(), y=Opt())(func_with_defaults)
wrapped_func_with_kw_only = wrap(x=Required(), y=Required())(func_with_kw_only)


async def async_func():
    pass


async def async_func_with_annotations(x: int):
    pass


async def async_func_with_defaults(x, y=3):
    pass


async def async_func_with_kw_only(x, *, y):
    pass


wrapped_async_func = wrap(async_func)
wrapped_async_func_with_annotations = wrap(x=Required())(async_func_with_annotations)
wrapped_async_func_with_defaults = wrap(x=Required(), y=Opt())(async_func_with_defaults)
wrapped_async_func_with_kw_only = wrap(x=Required(), y=Required())(async_func_with_kw_only)


class Klass:
    def method(self):
        pass

    def method_with_annotations(self, x: int):
        pass

    def method_with_defaults(self, x, y=3):
        pass

    def method_with_kw_only(self, x, *, y):
        pass

    wrapped_method = wrap(method)
    wrapped_method_with_annotations = wrap(x=Required())(method_with_annotations)
    wrapped_method_with_defaults = wrap(x=Required(), y=Opt())(method_with_defaults)
    wrapped_method_with_kw_only = wrap(x=Required(), y=Required())(method_with_kw_only)

    @staticmethod
    def cls():
        pass

    @staticmethod
    def cls_with_annotations(cls, x: int):
        pass

    @staticmethod
    def cls_with_defaults(cls, x, y=3):
        pass

    @staticmethod
    def cls_with_kw_only(cls, x, *, y):
        pass

    wrapped_cls = wrap(cls)
    wrapped_cls_with_annotations = wrap(x=Required())(cls_with_annotations)
    wrapped_cls_with_defaults = wrap(x=Required(), y=Opt())(cls_with_defaults)
    wrapped_cls_with_kw_only = wrap(x=Required(), y=Required())(cls_with_kw_only)

    @staticmethod
    def static():
        pass

    @staticmethod
    def static_with_annotations(x: int):
        pass

    @staticmethod
    def static_with_defaults(x, y=3):
        pass

    @staticmethod
    def static_with_kw_only(x, *, y):
        pass

    wrapped_static = wrap(static)
    wrapped_static_with_annotations = wrap(x=Required())(static_with_annotations)
    wrapped_static_with_defaults = wrap(x=Required(), y=Opt())(static_with_defaults)
    wrapped_static_with_kw_only = wrap(x=Required(), y=Required())(static_with_kw_only)

    async def async_method(self):
        pass

    async def async_method_with_annotations(self, x: int):
        pass

    async def async_method_with_defaults(self, x, y=3):
        pass

    async def async_method_with_kw_only(self, x, *, y):
        pass

    wrapped_async_method = wrap(async_method)
    wrapped_async_method_with_annotations = wrap(x=Required())(async_method_with_annotations)
    wrapped_async_method_with_defaults = wrap(x=Required(), y=Opt())(async_method_with_defaults)
    wrapped_async_method_with_kw_only = wrap(x=Required(), y=Required())(async_method_with_kw_only)

    @staticmethod
    async def async_cls():
        pass

    @staticmethod
    async def async_cls_with_annotations(cls, x: int):
        pass

    @staticmethod
    async def async_cls_with_defaults(cls, x, y=3):
        pass

    @staticmethod
    async def async_cls_with_kw_only(cls, x, *, y):
        pass

    wrapped_async_cls = wrap(async_cls)
    wrapped_async_cls_with_annotations = wrap(x=Required())(async_cls_with_annotations)
    wrapped_async_cls_with_defaults = wrap(x=Required(), y=Opt())(async_cls_with_defaults)
    wrapped_async_cls_with_kw_only = wrap(x=Required(), y=Required())(async_cls_with_kw_only)

    @staticmethod
    async def async_static():
        pass

    @staticmethod
    async def async_static_with_annotations(x: int):
        pass

    @staticmethod
    async def async_static_with_defaults(x, y=3):
        pass

    @staticmethod
    async def async_static_with_kw_only(x, *, y):
        pass

    wrapped_async_static = wrap(async_static)
    wrapped_async_static_with_annotations = wrap(x=Required())(async_static_with_annotations)
    wrapped_async_static_with_defaults = wrap(x=Required(), y=Opt())(async_static_with_defaults)
    wrapped_async_static_with_kw_only = wrap(x=Required(), y=Required())(async_static_with_kw_only)


instance = Klass()


@pytest.mark.parametrize(
    "original,wrapped,strict_is",
    [
        pytest.param(func, wrapped_func, True, id="func"),
        pytest.param(
            func_with_annotations, wrapped_func_with_annotations, True, id="func_with_annotations"
        ),
        pytest.param(func_with_defaults, wrapped_func_with_defaults, True, id="func_with_defaults"),
        pytest.param(func_with_kw_only, wrapped_func_with_kw_only, True, id="func_with_kw_only"),
        pytest.param(Klass.method, Klass.wrapped_method, True, id="Klass.method"),
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
        pytest.param(Klass.cls, Klass.wrapped_cls, True, id="Klass.cls"),
        pytest.param(
            Klass.cls_with_annotations,
            Klass.wrapped_cls_with_annotations,
            True,
            id="Klass.cls_with_annotations",
        ),
        pytest.param(
            Klass.cls_with_defaults,
            Klass.wrapped_cls_with_defaults,
            True,
            id="Klass.cls_with_defaults",
        ),
        pytest.param(
            Klass.cls_with_kw_only,
            Klass.wrapped_cls_with_kw_only,
            True,
            id="Klass.cls_with_kw_only",
        ),
        pytest.param(Klass.static, Klass.wrapped_static, True, id="Klass.static"),
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
        pytest.param(instance.method, instance.wrapped_method, False, id="instance.method"),
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
        pytest.param(instance.cls, instance.wrapped_cls, True, id="instance.cls"),
        pytest.param(
            instance.cls_with_annotations,
            instance.wrapped_cls_with_annotations,
            True,
            id="instance.cls_with_annotations",
        ),
        pytest.param(
            instance.cls_with_defaults,
            instance.wrapped_cls_with_defaults,
            True,
            id="instance.cls_with_defaults",
        ),
        pytest.param(
            instance.cls_with_kw_only,
            instance.wrapped_cls_with_kw_only,
            True,
            id="instance.cls_with_kw_only",
        ),
        pytest.param(instance.static, instance.wrapped_static, True, id="instance.static"),
        pytest.param(
            instance.static_with_annotations,
            instance.wrapped_static_with_annotations,
            True,
            id="instance.static_with_annotations",
        ),
        pytest.param(
            instance.static_with_defaults,
            instance.wrapped_static_with_defaults,
            True,
            id="instance.static_with_defaults",
        ),
        pytest.param(
            instance.static_with_kw_only,
            instance.wrapped_static_with_kw_only,
            True,
            id="instance.static_with_kw_only",
        ),
        pytest.param(Klass.async_method, Klass.wrapped_async_method, True, id="Klass.async_method"),
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
        pytest.param(Klass.async_cls, Klass.wrapped_async_cls, True, id="Klass.async_cls"),
        pytest.param(
            Klass.async_cls_with_annotations,
            Klass.wrapped_async_cls_with_annotations,
            True,
            id="Klass.async_cls_with_annotations",
        ),
        pytest.param(
            Klass.async_cls_with_defaults,
            Klass.wrapped_async_cls_with_defaults,
            True,
            id="Klass.async_cls_with_defaults",
        ),
        pytest.param(
            Klass.async_cls_with_kw_only,
            Klass.wrapped_async_cls_with_kw_only,
            True,
            id="Klass.async_cls_with_kw_only",
        ),
        pytest.param(Klass.async_static, Klass.wrapped_async_static, True, id="Klass.async_static"),
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
            instance.async_method, instance.wrapped_async_method, False, id="instance.async_method"
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
        pytest.param(instance.async_cls, instance.wrapped_async_cls, True, id="instance.async_cls"),
        pytest.param(
            instance.async_cls_with_annotations,
            instance.wrapped_async_cls_with_annotations,
            True,
            id="instance.async_cls_with_annotations",
        ),
        pytest.param(
            instance.async_cls_with_defaults,
            instance.wrapped_async_cls_with_defaults,
            True,
            id="instance.async_cls_with_defaults",
        ),
        pytest.param(
            instance.async_cls_with_kw_only,
            instance.wrapped_async_cls_with_kw_only,
            True,
            id="instance.async_cls_with_kw_only",
        ),
        pytest.param(
            instance.async_static, instance.wrapped_async_static, True, id="instance.async_static"
        ),
        pytest.param(
            instance.async_static_with_annotations,
            instance.wrapped_async_static_with_annotations,
            True,
            id="instance.async_static_with_annotations",
        ),
        pytest.param(
            instance.async_static_with_defaults,
            instance.wrapped_async_static_with_defaults,
            True,
            id="instance.async_static_with_defaults",
        ),
        pytest.param(
            instance.async_static_with_kw_only,
            instance.wrapped_async_static_with_kw_only,
            True,
            id="instance.async_static_with_kw_only",
        ),
    ],
)
def test_wrapped_attributes(original, wrapped, strict_is):
    assert (original is wrapped.__wrapped__) == strict_is, "is"
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
    else:
        assert func is wrapped.__func__

    try:
        func = original.__self__
    except AttributeError:
        with pytest.raises(AttributeError):
            wrapped.__self__
    else:
        assert func is wrapped.__self__

    if inspect.isfunction(original) != inspect.isfunction(wrapped):
        raise ValueError(f"{original.__class__!r} != {wrapped.__class__!r}")

    assert inspect.signature(original) == inspect.signature(wrapped), "signature"
    assert inspect.isfunction(original) == inspect.isfunction(wrapped), "isfunction"
    assert inspect.ismethod(original) == inspect.ismethod(wrapped), "ismethod"
    assert inspect.iscoroutinefunction(original) == inspect.iscoroutinefunction(
        wrapped
    ), "iscoroutinefunction"
    assert inspect.iscoroutine(original) == inspect.iscoroutine(wrapped), "iscoroutine"
