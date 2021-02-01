from typing import TYPE_CHECKING

import pytest

from antidote import Provide, inject, world
from antidote.core.exceptions import DoubleInjectionError
from antidote.core.wiring import Wiring, WithWiringMixin

if TYPE_CHECKING:
    pass


class MyService:
    pass


class AnotherService:
    pass


@pytest.fixture(params=['Wiring', 'wire'])
def wire(request):
    kind = request.param
    if kind == 'Wiring':
        def wire(**kwargs):
            return Wiring(**kwargs).wire

        return wire
    else:
        from antidote import wire
        return wire


@pytest.fixture(autouse=True)
def new_world():
    with world.test.empty():
        world.test.singleton({'x': object(),
                              'xx': object(),
                              'y': object(),
                              'z': object(),
                              MyService: MyService(),
                              AnotherService: AnotherService()})
        yield


@pytest.mark.parametrize('kwargs', [
    dict(dependencies=('x', 'y')),
    dict(dependencies=dict(x='x', y='y')),
])
def test_no_strict_validation(wire, kwargs):
    @wire(**kwargs)
    class A:
        def f(self, x):
            return x

        def g(self, x, y):
            return x, y

    a = A()
    assert a.f() == world.get("x")
    assert a.g() == (world.get("x"), world.get("y"))


def test_no_strict_validation_auto_provide(wire):
    @wire(auto_provide=[MyService, AnotherService])
    class A:
        def f(self, x: MyService):
            return x

        def g(self, x: MyService, y: AnotherService):
            return x, y

    a = A()
    assert a.f() == world.get(MyService)
    assert a.g() == (world.get(MyService), world.get(AnotherService))


def test_subclass_classmethod(wire):
    @wire(auto_provide=True)
    class Dummy:
        @classmethod
        def cls_method(cls, x: MyService):
            return cls, x

    assert (Dummy, world.get(MyService)) == Dummy.cls_method()

    class SubDummy(Dummy):
        pass

    assert (SubDummy, world.get(MyService)) == SubDummy.cls_method()


@pytest.mark.parametrize('kwargs, expectation', [
    (dict(methods=object()), pytest.raises(TypeError, match=".*method.*")),
    (dict(methods=[object()]), pytest.raises(TypeError, match="(?i).*method.*")),
    (dict(dependencies=object()), pytest.raises(TypeError, match=".*dependencies.*")),
    (dict(auto_provide=object()), pytest.raises(TypeError, match=".*auto_provide.*")),
    (dict(raise_on_double_injection=object()),
     pytest.raises(TypeError, match=".*raise_on_double_injection.*")),
])
def test_validation(wire, kwargs, expectation):
    with expectation:
        wire(**kwargs)


def test_iterable():
    w = Wiring(methods=iter(['method']),
               auto_provide=iter([MyService]))

    assert isinstance(w.methods, frozenset)
    assert w.methods == {'method'}
    assert isinstance(w.auto_provide, frozenset)
    assert w.auto_provide == {MyService}


def test_default_all_methods(wire):
    @wire()
    class A:
        def __init__(self, x: Provide[MyService]):
            self.x = x

        def __call__(self, x: Provide[MyService]):
            return x

        def method(self, x: Provide[MyService]):
            return x

        @classmethod
        def klass(cls, x: Provide[MyService]):
            return x

        @staticmethod
        def static(x: Provide[MyService]):
            return x

        def _method(self, x: Provide[MyService]):
            return x

        @classmethod
        def _klass(cls, x: Provide[MyService]):
            return x

        @staticmethod
        def _static(x: Provide[MyService]):
            return x

        def __method(self, x: Provide[MyService]):
            return x

        @classmethod
        def __klass(cls, x: Provide[MyService]):
            return x

        @staticmethod
        def __static(x: Provide[MyService]):
            return x

    a = A()
    dummy = world.get(MyService)
    assert a.x is dummy
    assert a() is dummy
    assert a.method() is dummy
    assert a.klass() is dummy
    assert a.static() is dummy
    assert a._method() is dummy
    assert a._klass() is dummy
    assert a._static() is dummy
    assert a._A__method() is dummy
    assert a._A__klass() is dummy
    assert a._A__static() is dummy


def test_methods(wire):
    @wire(methods=['f'], dependencies={'x': MyService})
    class A:
        def f(self, x):
            return x

        def g(self, x):
            return x

    assert A().f() is world.get(MyService)
    with pytest.raises(TypeError):
        A().g()

    with pytest.raises(AttributeError):
        @wire(methods=['f'])
        class A:
            pass


def test_double_injection(wire):
    @wire(methods=['f'])
    class A:
        @inject(auto_provide=True)  # auto_provide to force injection
        def f(self, x: MyService):
            return x

    assert A().f() is world.get(MyService)

    with pytest.raises(DoubleInjectionError):
        @wire(methods=['f'], raise_on_double_injection=True)
        class B:
            @inject(auto_provide=True)  # auto_provide to force injection
            def f(self, x: MyService):
                return x

    @wire()
    class C:
        @inject(auto_provide=True)  # auto_provide to force injection
        def f(self, x: MyService):
            return x

    assert C().f() is world.get(MyService)

    with pytest.raises(DoubleInjectionError):
        @wire(raise_on_double_injection=True)
        class D:
            @inject(auto_provide=True)  # auto_provide to force injection
            def f(self, x: MyService):
                return x


def test_invalid_methods(wire):
    with pytest.raises(TypeError, match='.*not_a_method.*'):
        @wire(methods=['not_a_method'])
        class Dummy:
            not_a_method = 1


@pytest.fixture(params=['method', 'classmethod', 'staticmethod'])
def wired_method_builder(request):
    kind = request.param

    def build(wire, *, annotation=object):
        if kind == 'method':
            @wire
            class A:
                def f(self, x: annotation):
                    return x
        elif kind == 'classmethod':
            @wire
            class A:
                @classmethod
                def f(cls, x: annotation):
                    return x
        else:
            @wire
            class A:
                @staticmethod
                def f(x: annotation):
                    return x
        return A().f

    return build


def test_use_inject_annotation(wire, wired_method_builder):
    f = wired_method_builder(wire())
    with pytest.raises(TypeError):
        f()

    f = wired_method_builder(wire(), annotation=Provide[MyService])
    assert f() is world.get(MyService)


def test_dependencies(wire, wired_method_builder):
    f = wired_method_builder(wire(methods=['f'], dependencies=('y',)))
    assert f() is world.get('y')

    f = wired_method_builder(wire(methods=['f'], dependencies=dict(x='z')))
    assert f() is world.get('z')

    f = wired_method_builder(wire(methods=['f'], dependencies=dict(y='z')))
    with pytest.raises(TypeError):
        f()

    f = wired_method_builder(wire(methods=['f'], dependencies=lambda arg: arg.name * 2))
    assert f() is world.get('xx')


@pytest.mark.parametrize('annotation', [object, MyService])
def test_wiring_auto_provide(wire, wired_method_builder, annotation):
    f = wired_method_builder(wire(methods=['f']),
                             annotation=annotation)
    with pytest.raises(TypeError):
        f()

    f = wired_method_builder(wire(methods=['f'], auto_provide=False),
                             annotation=annotation)
    with pytest.raises(TypeError):
        f()

    f = wired_method_builder(wire(methods=['f'], auto_provide=True),
                             annotation=annotation)
    if annotation is MyService:
        assert f() is world.get(MyService)
    else:
        with pytest.raises(TypeError):
            f()

    f = wired_method_builder(wire(methods=['f'], auto_provide=[MyService]),
                             annotation=annotation)
    if annotation is MyService:
        assert f() is world.get(MyService)
    else:
        with pytest.raises(TypeError):
            f()

    class Unknown:
        pass

    f = wired_method_builder(wire(methods=['f'], auto_provide=[Unknown]),
                             annotation=annotation)
    with pytest.raises(TypeError):
        f()


def test_complex_wiring(wire):
    @wire(auto_provide=True,
          methods=['g'])
    class A:
        def f(self, x: MyService):
            return x

        def g(self, x: MyService):
            return x

    with pytest.raises(TypeError):
        A().f()

    assert A().g() == world.get(MyService)


def test_class_static_methods(wire):
    @wire(methods=['static', 'klass'],
          auto_provide=True)  # auto_provide to force injection
    class Dummy:
        @staticmethod
        def static(x: MyService):
            pass

        @classmethod
        def klass(cls, x: MyService):
            pass

    assert isinstance(Dummy.__dict__['static'], staticmethod)
    assert isinstance(Dummy.__dict__['klass'], classmethod)


@pytest.mark.parametrize('kwargs', [
    dict(methods={'method', 'test'}),
    dict(dependencies=[MyService]),
    dict(auto_provide=True)
])
def test_copy(kwargs):
    wiring = Wiring(methods=['method'],
                    dependencies=dict(),
                    auto_provide=False)
    copy = wiring.copy(**kwargs)
    for key, value in kwargs.items():
        assert getattr(copy, key) == value


class DummyConf(WithWiringMixin):
    def __init__(self, wiring=None):
        self.wiring = wiring

    def copy(self, wiring):
        return DummyConf(wiring)


@pytest.mark.parametrize('kwargs', [
    dict(methods={'method', 'test'}),
    dict(dependencies=[MyService]),
    dict(auto_provide=True),
])
def test_with_wiring(kwargs):
    conf = DummyConf(Wiring(methods=['method'],
                            dependencies=dict(),
                            auto_provide=False))
    copy = conf.with_wiring(**kwargs)
    for key, value in kwargs.items():
        assert getattr(copy.wiring, key) == value

    kwargs.setdefault('methods', {'method'})
    copy = DummyConf().with_wiring(**kwargs)
    for key, value in kwargs.items():
        assert getattr(copy.wiring, key) == value
