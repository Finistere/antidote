"""
Test only that the wrapper behaves nicely in all cases.
Injection itself is tested through inject.
"""
from typing import Any, List, Tuple

import pytest

from antidote._internal.wrapper import InjectedWrapper, Injection, InjectionBlueprint
from antidote.core import DependencyContainer
from antidote.exceptions import DependencyNotFoundError

default_container = DependencyContainer()
sentinel = object()
sentinel_2 = object()
sentinel_3 = object()
default_container.update_singletons(dict(x=sentinel))

inject_self_x = [('self', True, None), ('x', True, 'x')]
inject_cls_x = [('cls', True, None), ('x', True, 'x')]
inject_x = [('x', True, 'x')]


def easy_wrap(func=None,
              arg_dependency: List[Tuple[str, bool, Any]] = tuple(),
              container: DependencyContainer = None):
    def wrapper(func):
        return InjectedWrapper(
            container=container or default_container,
            blueprint=InjectionBlueprint(tuple([
                Injection(arg_name, required, dependency)
                for arg_name, required, dependency in arg_dependency
            ])),
            wrapped=func
        )

    return func and wrapper(func) or wrapper


class Dummy:
    @easy_wrap(arg_dependency=inject_self_x)
    def method(self, x):
        return self, x

    @easy_wrap(arg_dependency=inject_cls_x)
    @classmethod
    def class_before(cls, x):
        return cls, x

    @classmethod
    @easy_wrap(arg_dependency=inject_cls_x)
    def class_after(cls, x):
        return cls, x

    @easy_wrap(arg_dependency=inject_x)
    @staticmethod
    def static_before(x):
        return x

    @staticmethod
    @easy_wrap(arg_dependency=inject_x)
    def static_after(x):
        return x


class Dummy2:
    def method(self, x):
        return self, x

    @classmethod
    def class_method(cls, x):
        return cls, x

    @staticmethod
    def static(x):
        return x


Dummy2.method = easy_wrap(Dummy2.__dict__['method'], inject_self_x)
Dummy2.class_method = easy_wrap(Dummy2.__dict__['class_method'], inject_cls_x)
Dummy2.static = easy_wrap(Dummy2.__dict__['static'], inject_x)


@easy_wrap(arg_dependency=inject_x)
def f(x):
    return x


d = Dummy()
d2 = Dummy2()


@pytest.mark.parametrize(
    'expected, func',
    [
        pytest.param(sentinel, f,
                     id='func'),

        pytest.param((sentinel_2, sentinel), Dummy.method,
                     id='method'),
        pytest.param((Dummy, sentinel), Dummy.class_before,
                     id='classmethod before'),
        pytest.param((Dummy, sentinel), Dummy.class_after,
                     id='classmethod after'),
        pytest.param(sentinel, Dummy.static_before,
                     id='staticmethod before'),
        pytest.param(sentinel, Dummy.static_after,
                     id='staticmethod after'),

        pytest.param((d, sentinel), d.method,
                     id='instance method'),
        pytest.param((Dummy, sentinel), d.class_before,
                     id='instance classmethod before'),
        pytest.param((Dummy, sentinel), d.class_after,
                     id='instance classmethod after'),
        pytest.param(sentinel, d.static_before,
                     id='instance staticmethod before'),
        pytest.param(sentinel, d.static_after,
                     id='instance staticmethod after'),

        pytest.param((d2, sentinel), d2.method,
                     id='post:instance method'),
        pytest.param((Dummy2, sentinel), d2.class_method,
                     id='post:instance classmethod'),
        pytest.param(sentinel, d2.static,
                     id='post:instance staticmethod'),

        pytest.param((sentinel_2, sentinel), Dummy2.method,
                     id='post:method'),
        pytest.param((Dummy2, sentinel), Dummy2.class_method,
                     id='post:classmethod'),
        pytest.param(sentinel, Dummy2.static,
                     id='post:staticmethod'),
    ]
)
def test_wrapper(expected, func):
    if expected == (sentinel_2, sentinel):
        assert expected == func(sentinel_2, sentinel)
        assert expected == func(sentinel_2)
        assert (sentinel_2, sentinel_3) == func(sentinel_2, sentinel_3)
        assert (sentinel_2, sentinel_3) == func(sentinel_2, x=sentinel_3)
    else:
        assert expected == func(sentinel)
        assert expected == func()

        if isinstance(expected, tuple):
            new_expected = (expected[0], sentinel_3)
        else:
            new_expected = sentinel_3

        assert new_expected == func(sentinel_3)
        assert new_expected == func(x=sentinel_3)


def test_classmethod_wrapping():
    def class_method(cls):
        pass

    class A:
        method = easy_wrap(classmethod(class_method))

    assert class_method == A.__dict__['method'].__func__
    assert A == A.method.__self__


def test_required_dependency_not_found():
    @easy_wrap(arg_dependency=[('x', True, 'unknown')])
    def f(x):
        return x

    with pytest.raises(DependencyNotFoundError):
        f()


def test_dependency_not_found():
    @easy_wrap(arg_dependency=[('x', False, 'unknown')])
    def f(x):
        return x

    with pytest.raises(TypeError):
        f()


def test_multiple_injections():
    container = DependencyContainer()
    xx = object()
    yy = object()
    zz = object()
    container.update_singletons(dict(xx=xx, yy=yy))

    @easy_wrap(arg_dependency=[('x', True, 'xx'),
                               ('y', True, 'yy'),
                               ('z', False, 'zz')],
               container=container)
    def f(x, y, z=zz):
        return x, y, z

    assert (xx, yy, zz) == f()
    assert (xx, sentinel, zz) == f(y=sentinel)
    assert (xx, yy, sentinel) == f(z=sentinel)
    assert (sentinel, yy, zz) == f(x=sentinel)
    assert (sentinel, yy, sentinel_2) == f(sentinel, z=sentinel_2)

    with pytest.raises(TypeError):
        f(sentinel, x=sentinel)


def g():
    pass


class G:
    original = staticmethod(g)
    wrapped = easy_wrap(original)


@pytest.mark.parametrize(
    'original,wrapped',
    [
        pytest.param(g, easy_wrap(g), id='function'),
        pytest.param(G.original, G.wrapped, id='staticmethod')
    ]
)
def test_wrap(original, wrapped):
    assert original.__module__ is wrapped.__module__
    assert original.__name__ is wrapped.__name__
    assert original.__qualname__ is wrapped.__qualname__
    assert original.__doc__ is wrapped.__doc__
    assert original.__annotations__ is wrapped.__annotations__

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
