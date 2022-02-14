import itertools
from typing import Any, Callable, Optional, Tuple, Type, Union

import pytest
from typing_extensions import Protocol

from antidote import Constants, Factory, Provide, Service, service, world
from antidote.core import Wiring


class Interface:
    pass


class FactoryOutput:
    pass


class FactoryOutput2:
    pass


class A:
    pass


class B:
    pass


@pytest.fixture(autouse=True)
def new_world():
    with world.test.new():
        world.test.singleton({A: A(),
                              B: B(),
                              'a': object(),
                              'b': object(),
                              'x': object(),
                              'y': object(),
                              'z': object()})
        yield


class DummyProtocol(Protocol):
    a: A
    b: B

    def __init__(self, a: A = None, b: B = None):
        pass

    def method_AB(self, a: A = None, b: B = None) -> Tuple[A, B]:
        pass

    def method_ab(self, a=None, b=None) -> Tuple[Any, Any]:
        pass

    def method_xyz(self, x=None, y=None, z=None) -> Tuple[Any, Any, Any]:
        pass


DEFAULT_WIRING = object()


def builder(cls_or_decorator: Union[type, Callable[..., Any]],
            wiring_kind: str = 'Wiring',
            subclass: bool = False):
    meta_kwargs = dict(abstract=True) if subclass else dict()
    if isinstance(cls_or_decorator, type):
        cls = cls_or_decorator

        def decorator(wiring=None):
            return lambda x: x
    else:
        cls = object
        decorator = cls_or_decorator

    def build(wiring: Wiring = None):
        decorate = (decorator(wiring=wiring)
                    if wiring is not DEFAULT_WIRING else
                    decorator())

        @decorate
        class Dummy(cls, **meta_kwargs):
            if wiring is not DEFAULT_WIRING and cls is not object:
                if wiring is not None:
                    if wiring_kind == 'Wiring':
                        __antidote__ = cls.Conf(wiring=wiring)
                    else:
                        __antidote__ = cls.Conf().with_wiring(**{
                            attr: getattr(wiring, attr)
                            for attr in Wiring.__slots__
                        })
                else:
                    __antidote__ = cls.Conf(wiring=None)

            def __init__(self, a: Provide[A] = None, b: Provide[B] = None):
                super().__init__()
                self.a = a
                self.b = b

            def method_AB(self, a: A = None, b: B = None) -> Tuple[A, B]:
                return a, b

            def method_ab(self, a=None, b=None) -> Tuple[Any, Any]:
                return a, b

            def method_xyz(self, x=None, y=None, z=None) -> Tuple[Any, Any, Any]:
                return x, y, z

            def __call__(self) -> FactoryOutput:  # for Factory
                pass

            def get(self):  # for Constants
                pass

        if subclass:
            class SubDummy(Dummy):
                def __call__(self) -> FactoryOutput2:  # for Factory
                    pass

            return SubDummy
        else:
            return Dummy

    return build


@pytest.fixture(params=[
    pytest.param((builder, service), id="@service"),
    *[
        pytest.param((builder, c, w), id=f"{c.__name__} - {w}")
        for (c, w) in itertools.product([Factory,
                                         Service,
                                         Constants],
                                        ['with_wiring', 'Wiring'])
    ]
])
def class_builder(request):
    f, *args = request.param
    return f(*args)


@pytest.fixture(params=[
    pytest.param((c, w), id=f"{c.__name__} - w")
    for (c, w) in itertools.product([Factory,
                                     Service,
                                     Constants],
                                    ['with_wiring', 'Wiring'])
])
def subclass_builder(request):
    (cls, wiring_kind) = request.param
    return builder(cls, wiring_kind, subclass=True)


F = Callable[[Optional[Wiring]], Type[DummyProtocol]]


def test_default(class_builder: F):
    dummy = class_builder(DEFAULT_WIRING)()
    assert dummy.a is world.get(A)
    assert dummy.b is world.get(B)

    (a, b) = dummy.method_AB()
    assert a is None
    assert b is None


def test_no_wiring(class_builder: F):
    dummy = class_builder(None)()
    assert dummy.a is None
    assert dummy.b is None


def test_methods(class_builder: F):
    dummy = class_builder(Wiring(methods=('__init__',)))()
    assert dummy.a is world.get(A)
    assert dummy.b is world.get(B)

    (a, b) = dummy.method_AB()
    assert a is None
    assert b is None

    dummy = class_builder(Wiring(methods=('method_AB',),
                                 auto_provide=True))()
    assert dummy.a is None
    assert dummy.b is None

    (a, b) = dummy.method_AB()
    assert a is world.get(A)
    assert b is world.get(B)


def test_auto_provide(class_builder: F):
    # Uses type hints by default
    dummy = class_builder(Wiring(methods=('method_AB',)))()
    (a, b) = dummy.method_AB()
    assert a is None
    assert b is None

    dummy = class_builder(Wiring(methods=('method_AB',), auto_provide=True))()
    (a, b) = dummy.method_AB()
    assert a is world.get(A)
    assert b is world.get(B)

    dummy = class_builder(Wiring(methods=('method_AB',), auto_provide=False))()
    (a, b) = dummy.method_AB()
    assert a is None
    assert b is None

    dummy = class_builder(Wiring(methods=('method_AB',), auto_provide=[A]))()
    (a, b) = dummy.method_AB()
    assert a is world.get(A)
    assert b is None

    dummy = class_builder(Wiring(methods=('method_AB',),
                                 auto_provide=lambda cls: True))()
    (a, b) = dummy.method_AB()
    assert a is world.get(A)
    assert b is world.get(B)

    dummy = class_builder(Wiring(methods=('method_AB',),
                                 auto_provide=lambda cls: issubclass(cls, A)))()
    (a, b) = dummy.method_AB()
    assert a is world.get(A)
    assert b is None

    dummy = class_builder(Wiring(methods=('method_AB',),
                                 auto_provide=lambda cls: False))()
    (a, b) = dummy.method_AB()
    assert a is None
    assert b is None


def test_dependencies_dict(class_builder: F):
    dummy = class_builder(Wiring(dependencies=dict(),
                                 auto_provide=True))()
    assert dummy.a is world.get(A)
    assert dummy.b is world.get(B)
    (a, b) = dummy.method_AB()
    assert a is world.get(A)
    assert b is world.get(B)
    (a, b) = dummy.method_ab()
    assert a is None
    assert b is None

    dummy = class_builder(Wiring(dependencies=dict(a='x', b='y'),
                                 auto_provide=True))()
    assert dummy.a is world.get(A)
    assert dummy.b is world.get(B)
    (a, b) = dummy.method_AB()
    assert a is world.get('x')
    assert b is world.get('y')
    (a, b) = dummy.method_ab()
    assert a is world.get('x')
    assert b is world.get('y')

    dummy = class_builder(Wiring(dependencies=dict(b='y'),
                                 auto_provide=True))()
    assert dummy.a is world.get(A)
    assert dummy.b is world.get(B)
    (a, b) = dummy.method_AB()
    assert a is world.get(A)
    assert b is world.get('y')
    (a, b) = dummy.method_ab()
    assert a is None
    assert b is world.get('y')


def test_dependencies_seq(class_builder: F):
    dummy = class_builder(Wiring(dependencies=[],
                                 auto_provide=True))()
    assert dummy.a is world.get(A)
    assert dummy.b is world.get(B)
    (a, b) = dummy.method_AB()
    assert a is world.get(A)
    assert b is world.get(B)
    (a, b) = dummy.method_ab()
    assert a is None
    assert b is None

    dummy = class_builder(Wiring(dependencies=[None, None],
                                 auto_provide=True))()
    assert dummy.a is world.get(A)
    assert dummy.b is world.get(B)
    (a, b) = dummy.method_AB()
    assert a is world.get(A)
    assert b is world.get(B)
    (a, b) = dummy.method_ab()
    assert a is None
    assert b is None

    dummy = class_builder(Wiring(dependencies=['x', 'y'],
                                 auto_provide=True))()
    assert dummy.a is world.get(A)
    assert dummy.b is world.get(B)
    (a, b) = dummy.method_AB()
    assert a is world.get('x')
    assert b is world.get('y')
    (a, b) = dummy.method_ab()
    assert a is world.get('x')
    assert b is world.get('y')

    dummy = class_builder(Wiring(dependencies=[None, 'y'],
                                 auto_provide=True))()
    assert dummy.a is world.get(A)
    assert dummy.b is world.get(B)
    (a, b) = dummy.method_AB()
    assert a is world.get(A)
    assert b is world.get('y')
    (a, b) = dummy.method_ab()
    assert a is None
    assert b is world.get('y')

    dummy = class_builder(Wiring(dependencies=['x', None],
                                 auto_provide=True))()
    assert dummy.a is world.get(A)
    assert dummy.b is world.get(B)
    (a, b) = dummy.method_AB()
    assert a is world.get('x')
    assert b is world.get(B)
    (a, b) = dummy.method_ab()
    assert a is world.get('x')
    assert b is None


def test_dependencies_callable(class_builder: F):
    dummy = class_builder(Wiring(dependencies=lambda arg: None,
                                 auto_provide=True))()
    assert dummy.a is world.get(A)
    assert dummy.b is world.get(B)
    (a, b) = dummy.method_AB()
    assert a is world.get(A)
    assert b is world.get(B)
    (a, b) = dummy.method_ab()
    assert a is None
    assert b is None

    dummy = class_builder(Wiring(dependencies=lambda arg: 'x' if arg.name == 'a' else 'y',
                                 auto_provide=True))()
    assert dummy.a is world.get(A)
    assert dummy.b is world.get(B)
    (a, b) = dummy.method_AB()
    assert a is world.get('x')
    assert b is world.get('y')
    (a, b) = dummy.method_ab()
    assert a is world.get('x')
    assert b is world.get('y')

    dummy = class_builder(Wiring(
        dependencies=lambda arg: 'x' if arg.name == 'a' else None,
        auto_provide=True))()
    assert dummy.a is world.get(A)
    assert dummy.b is world.get(B)
    (a, b) = dummy.method_AB()
    assert a is world.get('x')
    assert b is world.get(B)
    (a, b) = dummy.method_ab()
    assert a is world.get('x')
    assert b is None


def test_distinct_arguments(class_builder: F):
    # Having more arguments in dependencies seq is not an issue for methods having less.
    dummy = class_builder(Wiring(methods=('method_AB', 'method_xyz'),
                                 dependencies=['x', None, 'z'],
                                 auto_provide=True))()
    (a, b) = dummy.method_AB()
    assert a is world.get('x')
    assert b is world.get(B)
    (x, y, z) = dummy.method_xyz()
    assert x is world.get('x')
    assert y is None
    assert z is world.get('z')

    # Unknown argument in the dependencies dict won't raise an error.
    dummy = class_builder(Wiring(methods=('method_AB', 'method_xyz'),
                                 dependencies=dict(b='b', y='y'),
                                 auto_provide=True))()
    (a, b) = dummy.method_AB()
    assert a is world.get(A)
    assert b is world.get('b')
    (x, y, z) = dummy.method_xyz()
    assert x is None
    assert y is world.get('y')
    assert z is None

    # type_hints
    dummy = class_builder(Wiring(methods=('method_AB', 'method_xyz'),
                                 auto_provide=[A]))()
    (a, b) = dummy.method_AB()
    assert a is world.get(A)
    assert b is None
    (x, y, z) = dummy.method_xyz()
    assert x is None
    assert y is None
    assert z is None
