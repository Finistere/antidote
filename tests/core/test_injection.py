import typing

import pytest

from antidote import world
from antidote._internal.argspec import Arguments
from antidote.core import DependencyContainer, raw_inject
from antidote.exceptions import DependencyNotFoundError


class Service:
    pass


class AnotherService:
    pass


def test_simple():
    @raw_inject
    def f(x: Service):
        return x

    with world.test.empty():
        s = Service()
        world.singletons.set(Service, s)
        assert s == f()


@pytest.mark.parametrize(
    'expected,kwargs',
    [
        pytest.param((None, None),
                     dict(),
                     id='nothing'),
        pytest.param((Service, None),
                     dict(dependencies=dict(first=Service)),
                     id='dependencies:dict-first'),
        pytest.param((Service, None),
                     dict(dependencies=(Service,)),
                     id='dependencies:tuple-first'),
        pytest.param((None, Service),
                     dict(dependencies=dict(second=Service)),
                     id='dependencies:dict-second'),
        pytest.param((None, Service),
                     dict(dependencies=(None, Service)),
                     id='dependencies:tuple-second'),
        pytest.param(('first', 'second'),
                     dict(dependencies=lambda s: s),
                     id='dependencies:callable'),
        pytest.param((Service, Service),
                     dict(dependencies=lambda s: Service),
                     id='dependencies:callable2'),
        pytest.param((None, None),
                     dict(dependencies=lambda s: None),
                     id='dependencies:callable3'),
        pytest.param(('first', 'second'),
                     dict(dependencies="{arg_name}"),
                     id='dependencies:str'),
        pytest.param(('prefix:first', 'prefix:second'),
                     dict(dependencies="prefix:{arg_name}"),
                     id='dependencies:str2'),
        pytest.param(('first', 'second'),
                     dict(use_names=True),
                     id='use_names:True'),
        pytest.param((None, None),
                     dict(use_names=False),
                     id='use_names:False'),
        pytest.param((None, 'second'),
                     dict(use_names=['second']),
                     id='use_names:list')
    ]
)
def test_without_type_hints(expected, kwargs):
    default = object()

    @raw_inject(**kwargs)
    def f(first=default, second=default):
        return first, second

    class A:
        @raw_inject(**kwargs)
        def method(self, first=default, second=default):
            return first, second

        @raw_inject(**kwargs)
        @classmethod
        def class_method(cls, first=default, second=default):
            return first, second

        @raw_inject(**kwargs)
        @staticmethod
        def static_method(first=default, second=default):
            return first, second

    with world.test.empty():
        world.singletons.update({
            Service: Service(),
            AnotherService: AnotherService(),
            'first': object(),
            'second': object(),
            'prefix:first': object(),
            'prefix:second': object()
        })

        expected = tuple((
            world.get(d) if d is not None else default
            for d in expected
        ))
        assert expected == f()
        assert expected == A().method()
        assert expected == A.class_method()
        assert expected == A.static_method()

        a, b = object(), object()
        assert (a, b) == f(a, b)
        assert (a, b) == A().method(a, b)
        assert (a, b) == A.class_method(a, b)
        assert (a, b) == A.static_method(a, b)


@pytest.mark.parametrize(
    'expected, kwargs',
    [
        pytest.param((Service, None),
                     dict(),
                     id='nothing'),
        pytest.param((Service, None),
                     dict(dependencies=dict(first=Service)),
                     id='dependencies:dict-first'),
        pytest.param((Service, None),
                     dict(dependencies=(Service,)),
                     id='dependencies:tuple-first'),
        pytest.param((Service, Service),
                     dict(dependencies=dict(second=Service)),
                     id='dependencies:dict-second'),
        pytest.param((Service, Service),
                     dict(dependencies=(None, Service)),
                     id='dependencies:tuple-second'),
        pytest.param(('first', 'second'),
                     dict(dependencies=lambda s: s),
                     id='dependencies:callable'),
        pytest.param((Service, Service),
                     dict(dependencies=lambda s: Service),
                     id='dependencies:callable2'),
        pytest.param((Service, None),
                     dict(dependencies=lambda s: None),
                     id='dependencies:callable3'),
        pytest.param(('first', 'second'),
                     dict(dependencies="{arg_name}"),
                     id='dependencies:str'),
        pytest.param(('prefix:first', 'prefix:second'),
                     dict(dependencies="prefix:{arg_name}"),
                     id='dependencies:str2'),
        pytest.param((Service, 'second'),
                     dict(use_names=True),
                     id='use_names:True'),
        pytest.param((Service, None),
                     dict(use_names=False),
                     id='use_names:False'),
        pytest.param((Service, None),
                     dict(use_names=['first']),
                     id='use_names:list-first'),
        pytest.param((Service, 'second'),
                     dict(use_names=['second']),
                     id='use_names:list-second'),
        pytest.param((Service, None),
                     dict(use_type_hints=True),
                     id='use_type_hints:True'),
        pytest.param((Service, None),
                     dict(use_type_hints=['first']),
                     id='use_type_hints:list-first'),
        pytest.param((Service, 'second'),
                     dict(use_type_hints=['first'], use_names=True),
                     id='use_type_hints:list-first+use_names=True'),
        pytest.param((None, None),
                     dict(use_type_hints=['second']),
                     id='use_type_hints:list-second'),
        pytest.param(('first', 'second'),
                     dict(use_type_hints=['second'], use_names=True),
                     id='use_type_hints:list-second+use_names=True'),
        pytest.param((None, None),
                     dict(use_type_hints=False),
                     id='use_type_hints:False'),
        pytest.param(('first', 'second'),
                     dict(use_type_hints=False, use_names=True),
                     id='use_type_hints:False+use_names=True'),
    ]
)
def test_with_type_hints(expected, kwargs):
    default = object()

    @raw_inject(**kwargs)
    def f(first: Service = default, second: str = default):
        return first, second

    class A:
        @raw_inject(**kwargs)
        def method(self, first: Service = default, second: str = default):
            return first, second

        @raw_inject(**kwargs)
        @classmethod
        def class_method(cls, first: Service = default, second: str = default):
            return first, second

        @raw_inject(**kwargs)
        @staticmethod
        def static_method(first: Service = default, second: str = default):
            return first, second

    with world.test.empty():
        world.singletons.update({Service: Service(),
                                 AnotherService: AnotherService(),
                                 'first': object(),
                                 'second': object(),
                                 'prefix:first': object(),
                                 'prefix:second': object()})

        expected = tuple((
            world.get(d) if d is not None else default
            for d in expected
        ))
        assert expected == f()
        assert expected == A().method()
        assert expected == A.class_method()
        assert expected == A.static_method()

        a, b = object(), object()
        assert (a, b) == f(a, b)
        assert (a, b) == A().method(a, b)
        assert (a, b) == A.class_method(a, b)
        assert (a, b) == A.static_method(a, b)


@pytest.mark.parametrize(
    'type_hint',
    [str, int, float, set, list, dict, complex, type, tuple, bytes, bytearray,
     typing.Optional, typing.Sequence]
)
def test_ignored_type_hints(type_hint):
    @raw_inject
    def f(x: type_hint):
        pass

    with world.test.empty():
        world.singletons.set(type_hint, object())
        with pytest.raises(TypeError):
            f()


def test_arguments():
    def f(a, b):
        pass

    arguments = Arguments.from_callable(f)

    @raw_inject(arguments=arguments, use_names=True)
    def g(**kwargs):
        return kwargs

    with world.test.empty():
        world.singletons.update(dict(a=12, b=24))
        assert dict(a=12, b=24) == g()


def test_none_optional_support():
    class Dummy:
        pass

    @raw_inject
    def f(x: Service = None):
        return x

    @raw_inject
    def g(x: typing.Optional[Service] = None):
        return x

    @raw_inject
    def h(x: Dummy, y: typing.Optional[Service] = None):
        return y

    @raw_inject
    def f2(x: typing.Union[Service, Dummy]):
        pass

    with world.test.empty():
        s = Service()
        world.singletons.set(Dummy, Dummy())
        world.singletons.set(Service, s)
        assert s == f()
        assert s == g()
        assert s == h()
        with pytest.raises(TypeError):
            f2()

    with world.test.empty():
        world.singletons.set(Dummy, Dummy())
        assert f() is None
        assert g() is None
        assert h() is None


@pytest.mark.parametrize(
    'error,kwargs',
    [
        pytest.param(TypeError,
                     dict(),
                     id="unknown-dependency"),
        pytest.param(DependencyNotFoundError,
                     dict(dependencies=(Service,)),
                     id="dependencies:unknown-dependency-tuple"),
        pytest.param(DependencyNotFoundError,
                     dict(dependencies=dict(x=Service)),
                     id="dependencies:unknown-dependency-dict"),
        pytest.param(DependencyNotFoundError,
                     dict(dependencies=lambda s: Service),
                     id="dependencies:unknown-dependency-callable"),
        pytest.param(DependencyNotFoundError,
                     dict(dependencies="unknown:{arg_name}"),
                     id="dependencies:unknown-dependency-str"),
        pytest.param((ValueError, TypeError),
                     dict(dependencies=(None, None)),
                     id="dependencies:too-much-arguments"),
        pytest.param(TypeError,
                     dict(dependencies=object()),
                     id="dependencies:unsupported-type"),
        pytest.param(TypeError,
                     dict(dependencies={1: 'x'}),
                     id="dependencies:invalid-key-type"),
        pytest.param(ValueError,
                     dict(dependencies=dict(unknown=DependencyContainer)),
                     id="dependencies:unknown-argument-dict"),
        pytest.param(TypeError,
                     dict(use_names=False),
                     id="use_names:unknown-dependency-False"),
        pytest.param(DependencyNotFoundError,
                     dict(use_names=True),
                     id="use_names:unknown-dependency-True"),
        pytest.param(DependencyNotFoundError,
                     dict(use_names=['x']),
                     id="use_names:unknown-dependency-list"),
        pytest.param(ValueError,
                     dict(use_names=['y']),
                     id="use_names:unknown-argument-list"),
        pytest.param(ValueError,
                     dict(use_names=['x', 'y']),
                     id="use_names:unknown-argument-list2"),
        pytest.param(TypeError,
                     dict(use_names=[]),
                     id="use_names:empty"),
        pytest.param(TypeError,
                     dict(use_names=object()),
                     id="use_names:unsupported-type"),
        pytest.param(TypeError,
                     dict(use_names=[1]),
                     id="use_names:invalid-name-type"),
        pytest.param(TypeError,
                     dict(use_type_hints=object()),
                     id="use_type_hints:unsupported-type"),
        pytest.param(TypeError,
                     dict(use_type_hints=[1]),
                     id="use_type_hints:invalid-name-type"),
        pytest.param(ValueError,
                     dict(use_type_hints=['y']),
                     id="use_type_hints:unknown-arg"),
    ]
)
def test_invalid(error, kwargs):
    with pytest.raises(error):
        @raw_inject(**kwargs)
        def f(x):
            return x

        f()

    with pytest.raises(error):
        class A:
            @raw_inject(**kwargs)
            def method(self, x):
                return x

        A().method()

    with pytest.raises(error):
        class A:
            @raw_inject(**kwargs)
            @classmethod
            def classmethod(cls, x):
                return x

        A.classmethod()

    with pytest.raises(error):
        class A:
            @raw_inject(**kwargs)
            @staticmethod
            def staticmethod(x):
                return x

        A.staticmethod()


@pytest.mark.parametrize(
    'error,kwargs',
    [
        pytest.param(ValueError,
                     dict(dependencies=dict(self='x')),
                     id="dependencies"),
        pytest.param(ValueError,
                     dict(use_names=('self',)),
                     id="use_names"),
        pytest.param(ValueError,
                     dict(use_type_hints=('self',)),
                     id="use_type_hints"),
    ]
)
def test_cannot_inject_self(error, kwargs):
    with pytest.raises(error):
        class A:
            @raw_inject(**kwargs)
            def method(self, x=None):
                return x

        A()

    with pytest.raises(error):
        class A:
            @raw_inject(**kwargs)
            @classmethod
            def classmethod(self, x=None):
                return x

        A()


def test_invalid_type_hint():
    @raw_inject
    def f(x: Service):
        return x

    with pytest.raises(DependencyNotFoundError):
        f()


def test_no_injections():
    def f(x):
        return x

    # When nothing can be injected, the same function should be returned
    assert raw_inject(f) is f


def test_already_injected():
    @raw_inject(use_names=True)
    def f(x):
        return x

    # When the function has already its arguments injected, the same function should
    # be returned
    assert raw_inject(f) is f


def test_class_inject():
    with pytest.raises(TypeError):
        @raw_inject
        class Dummy:
            pass
