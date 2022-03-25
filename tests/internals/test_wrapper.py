"""
Test only that the wrapper behaves nicely in all cases.
Injection itself is tested through inject.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from antidote import world
from antidote._internal.wrapper import build_wrapper, Injection, InjectionBlueprint
from antidote.exceptions import DependencyNotFoundError

A = object()
B = object()
C = object()


@pytest.fixture(autouse=True, scope='module')
def empty_world():
    with world.test.empty():
        world.test.singleton('x', A)
        yield


class Arg:
    dependency: object


@dataclass
class Required(Arg):
    dependency: object = field(default=None)


@dataclass
class Opt(Arg):
    dependency: object = field(default=None)


def wrap(__func=None, **kwargs: Arg):
    def wrapper(func):
        return build_wrapper(
            blueprint=InjectionBlueprint(tuple([
                Injection(
                    arg_name=arg_name,
                    required=isinstance(dependency, Required),
                    dependency=dependency.dependency,
                    optional=False
                )
                for arg_name, dependency in kwargs.items()
            ])),
            wrapped=func
        )

    return __func and wrapper(__func) or wrapper


class Dummy:
    @wrap(self=Required(None), x=Required('x'))
    def method(self, x):
        return self, x

    @classmethod
    @wrap(cls=Required(None), x=Required('x'))
    def class_after(cls, x):
        return cls, x

    @staticmethod
    @wrap(x=Required('x'))
    def static_after(x):
        return x


class Dummy2:
    def method(self, x):
        return self, x


Dummy2.method = wrap(Dummy2.__dict__['method'], self=Required(None), x=Required('x'))


@wrap(x=Required('x'))
def f(x):
    return x


d = Dummy()
d2 = Dummy2()


@pytest.mark.parametrize(
    'expected, func',
    [
        pytest.param(A, f,
                     id='func'),

        pytest.param((B, A), Dummy.method,
                     id='method'),
        pytest.param((Dummy, A), Dummy.class_after,
                     id='classmethod after'),
        pytest.param(A, Dummy.static_after,
                     id='staticmethod after'),

        pytest.param((d, A), d.method,
                     id='instance method'),
        pytest.param((Dummy, A), d.class_after,
                     id='instance classmethod after'),
        pytest.param(A, d.static_after,
                     id='instance staticmethod after'),

        pytest.param((d2, A), d2.method,
                     id='post:instance method'),
        pytest.param((B, A), Dummy2.method,
                     id='post:method')
    ]
)
def test_wrapper(expected, func: Any):
    if expected == (B, A):
        assert expected == func(B, A)
        assert expected == func(B)
        assert (B, C) == func(B, C)
        assert (B, C) == func(B, x=C)
    else:
        assert expected == func(A)
        assert expected == func()

        if isinstance(expected, tuple):
            new_expected = (expected[0], C)
        else:
            new_expected = C

        assert new_expected == func(C)
        assert new_expected == func(x=C)


def test_classmethod_wrapping():
    def class_method(cls):
        pass

    class A:
        method = wrap(classmethod(class_method))

    assert class_method == A.__dict__['method'].__func__
    assert A == A.method.__self__


def test_required_dependency_not_found():
    @wrap(x=Required('unknown'))
    def f(x):
        return x

    with pytest.raises(DependencyNotFoundError):
        f()


def test_dependency_not_found():
    @wrap(x=Opt('unknown'))
    def f(x):
        return x

    with pytest.raises(TypeError):
        f()


def test_multiple_injections():
    xx = object()
    yy = object()
    zz = object()

    @wrap(x=Required('xx'), y=Required('yy'), z=Opt('zz'))
    def f(x, y, z=zz):
        return x, y, z

    world.test.singleton(dict(xx=xx, yy=yy))
    assert (xx, yy, zz) == f()
    assert (xx, A, zz) == f(y=A)
    assert (xx, yy, A) == f(z=A)
    assert (A, yy, zz) == f(x=A)
    assert (A, yy, B) == f(A, z=B)

    with pytest.raises(TypeError):
        f(A, x=A)


def f():
    pass


async def async_f():
    pass


@pytest.mark.parametrize('func', [f, async_f])
def test_custom_attributes(func):
    func.attr = "test"
    func.another_attr = "another_attr"
    wrapped = wrap(func)
    assert "test" == wrapped.attr

    wrapped.attr2 = "test2"
    assert "test2" == wrapped.attr2
    # After setting a new attribute, original ones should still be accessible.
    assert "test" == wrapped.attr

    wrapped.attr = "overridden test"
    assert "overridden test" == wrapped.attr

    # You should be able to remove new attributes
    del wrapped.attr2

    with pytest.raises(AttributeError):
        wrapped.attr2

    # but not existing ones
    with pytest.raises(AttributeError):
        del wrapped.another_attr


@pytest.mark.asyncio
async def test_async_wrapper():
    with world.test.empty():
        world.test.singleton(dict(a=A, b=B, c=C))

        @wrap(x=Required('a'))
        async def f(x):
            return x

        res = await f()
        assert res == A

        class Dummy:
            @wrap(self=Required(), x=Required('a'))
            async def method(self, x):
                return x

            @classmethod
            @wrap(cls=Required(), x=Required('a'))
            async def klass(cls, x):
                return x

            @staticmethod
            @wrap(x=Required('a'))
            async def static(x):
                return x

        d = Dummy()
        print(d.__dict__)
        res = await d.method()
        assert res == A
        res = await d.klass()
        assert res == A
        res = await d.static()
        assert res == A
        res = await Dummy.klass()
        assert res == A
        res = await Dummy.static()
        assert res == A

        @wrap(x=Required('a'), y=Required('b'), z=Opt('unknown'))
        async def f(x, y, z=None):
            return x, y, z

        (x, y, z) = await f()
        assert x == A
        assert y == B
        assert z is None

        @wrap(x=Required('a'), y=Required('b'), z=Required('unknown'))
        async def f(x, y, z):
            pass

        with pytest.raises(DependencyNotFoundError, match='.*unknown.*'):
            await f()

        @wrap(x=Required('a'), y=Required('b'), z=Required())
        async def f(x, y, z):
            pass

        with pytest.raises(TypeError):
            await f()
