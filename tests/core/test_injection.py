import typing

import pytest

from antidote._internal.argspec import Arguments
from antidote.core import DependencyContainer, inject
from antidote.exceptions import DependencyNotFoundError


class Service:
    pass


class AnotherService:
    pass


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
    container = DependencyContainer()
    container.update_singletons({Service: Service()})
    container.update_singletons({AnotherService: AnotherService()})
    container.update_singletons({'first': object()})
    container.update_singletons({'second': object()})
    container.update_singletons({'prefix:first': object()})
    container.update_singletons({'prefix:second': object()})
    default = object()

    @inject(container=container, **kwargs)
    def f(first=default, second=default):
        return first, second

    class A:
        @inject(container=container, **kwargs)
        def method(self, first=default, second=default):
            return first, second

        @inject(container=container, **kwargs)
        @classmethod
        def class_method(cls, first=default, second=default):
            return first, second

        @inject(container=container, **kwargs)
        @staticmethod
        def static_method(first=default, second=default):
            return first, second

    expected = tuple((
        container.get(d) if d is not None else default
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
    container = DependencyContainer()
    container.update_singletons({Service: Service(),
                                 AnotherService: AnotherService(),
                                 'first': object(),
                                 'second': object(),
                                 'prefix:first': object(),
                                 'prefix:second': object()})
    default = object()

    @inject(container=container, **kwargs)
    def f(first: Service = default, second: str = default):
        return first, second

    class A:
        @inject(container=container, **kwargs)
        def method(self, first: Service = default, second: str = default):
            return first, second

        @inject(container=container, **kwargs)
        @classmethod
        def class_method(cls, first: Service = default, second: str = default):
            return first, second

        @inject(container=container, **kwargs)
        @staticmethod
        def static_method(first: Service = default, second: str = default):
            return first, second

    expected = tuple((
        container.get(d) if d is not None else default
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
    container = DependencyContainer()
    container.update_singletons({type_hint: object()})

    @inject(container=container)
    def f(x: type_hint):
        pass

    with pytest.raises(TypeError):
        f()


def test_arguments():
    container = DependencyContainer()
    container.update_singletons(dict(a=12, b=24))

    def f(a, b):
        pass

    arguments = Arguments.from_callable(f)

    @inject(arguments=arguments, use_names=True, container=container)
    def g(**kwargs):
        return kwargs

    assert dict(a=12, b=24) == g()


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
    container = DependencyContainer()

    with pytest.raises(error):
        @inject(container=container, **kwargs)
        def f(x):
            return x

        f()

    with pytest.raises(error):
        class A:
            @inject(container=container, **kwargs)
            def method(self, x):
                return x

        A().method()

    with pytest.raises(error):
        class A:
            @inject(container=container, **kwargs)
            @classmethod
            def classmethod(cls, x):
                return x

        A.classmethod()

    with pytest.raises(error):
        class A:
            @inject(container=container, **kwargs)
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
    container = DependencyContainer()
    container.update_singletons(dict(x=object(), y=object()))

    with pytest.raises(error):
        class A:
            @inject(container=container, **kwargs)
            def method(self, x=None):
                return x
        A()

    with pytest.raises(error):
        class A:
            @inject(container=container, **kwargs)
            @classmethod
            def classmethod(self, x=None):
                return x
        A()


def test_invalid_type_hint():
    @inject(container=DependencyContainer())
    def f(x: Service):
        return x

    with pytest.raises(DependencyNotFoundError):
        f()


def test_no_injections():
    container = DependencyContainer()

    def f(x):
        return x

    injected_f = inject(f, container=container)

    # When nothing can be injected, the same function should be returned
    assert injected_f is f


def test_already_injected():
    container = DependencyContainer()

    @inject(container=container, use_names=True)
    def f(x):
        return x

    injected_f = inject(f, container=container)

    # When the function has already its arguments injected, the same function should
    # be returned
    assert injected_f is f


def test_class_inject():
    container = DependencyContainer()
    with pytest.raises(TypeError):
        @inject(container=container)
        class Dummy:
            pass
