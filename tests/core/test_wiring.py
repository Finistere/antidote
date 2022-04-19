from __future__ import annotations

from dataclasses import dataclass

import pytest

from antidote import inject, Provide, world
from antidote.core.exceptions import DoubleInjectionError
from antidote.core.wiring import Wiring, WithWiringMixin


class MyService:
    pass


class AnotherService:
    pass


@pytest.fixture(params=['Wiring', 'wire'])
def wire_(request):
    kind = request.param
    if kind == 'Wiring':
        def wire(**kwargs):
            type_hints_locals = kwargs.pop('type_hints_locals', None)
            wiring = Wiring(**kwargs)

            def decorator(cls: type) -> type:
                wiring.wire(klass=cls, type_hints_locals=type_hints_locals)
                return cls

            return decorator

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
def test_no_strict_validation(wire_, kwargs):
    @wire_(**kwargs)
    class A:
        def f(self, x):
            return x

        def g(self, x, y):
            return x, y

    a = A()
    assert a.f() == world.get("x")
    assert a.g() == (world.get("x"), world.get("y"))


def test_no_strict_validation_auto_provide(wire_):
    @wire_(auto_provide=[MyService, AnotherService])
    class A:
        def f(self, x: MyService):
            return x

        def g(self, x: MyService, y: AnotherService):
            return x, y

    a = A()
    assert a.f() == world.get(MyService)
    assert a.g() == (world.get(MyService), world.get(AnotherService))


def test_subclass_classmethod(wire_):
    @wire_(auto_provide=True)
    class Dummy:
        @classmethod
        def cls_method(cls, x: MyService):
            return cls, x

    assert (Dummy, world.get(MyService)) == Dummy.cls_method()

    class SubDummy(Dummy):
        pass

    assert (SubDummy, world.get(MyService)) == SubDummy.cls_method()


@pytest.mark.parametrize('arg',
                         ['methods', 'dependencies', 'auto_provide', 'raise_on_double_injection',
                          'ignore_type_hints', 'type_hints_locals'])
def test_invalid_arguments(wire_, arg: str) -> None:
    with pytest.raises(TypeError, match=".*" + arg + ".*"):
        @wire_(**{arg: object()})  # type: ignore
        class Dummy:
            pass


def test_invalid_class(wire_):
    with pytest.raises(TypeError):
        wire_()(object())


def test_iterable():
    w = Wiring(methods=iter(['method']),
               auto_provide=iter([MyService]))

    assert isinstance(w.methods, frozenset)
    assert w.methods == {'method'}
    assert isinstance(w.auto_provide, frozenset)
    assert w.auto_provide == {MyService}


def test_default_all_methods(wire_):
    @wire_()
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


def test_methods(wire_):
    @wire_(methods=['f'], dependencies={'x': MyService})
    class A:
        def f(self, x):
            return x

        def g(self, x):
            return x

    assert A().f() is world.get(MyService)
    with pytest.raises(TypeError):
        A().g()

    with pytest.raises(AttributeError):
        @wire_(methods=['f'])
        class A:
            pass


def test_double_injection(wire_):
    @wire_(methods=['f'])
    class A:
        @inject(auto_provide=True)  # auto_provide to force injection
        def f(self, x: MyService):
            return x

    assert A().f() is world.get(MyService)

    with pytest.raises(DoubleInjectionError):
        @wire_(methods=['f'], raise_on_double_injection=True)
        class B:
            @inject(auto_provide=True)  # auto_provide to force injection
            def f(self, x: MyService):
                return x

    @wire_()
    class C:
        @inject(auto_provide=True)  # auto_provide to force injection
        def f(self, x: MyService):
            return x

    assert C().f() is world.get(MyService)

    with pytest.raises(DoubleInjectionError):
        @wire_(raise_on_double_injection=True)
        class D:
            @inject(auto_provide=True)  # auto_provide to force injection
            def f(self, x: MyService):
                return x


def test_invalid_methods(wire_):
    with pytest.raises(TypeError, match='.*not_a_method.*'):
        @wire_(methods=['not_a_method'])
        class Dummy:
            not_a_method = 1

    with pytest.raises(TypeError, match='.*methods.*'):
        wire_(methods=[object()])


@pytest.fixture(params=['method', 'classmethod', 'staticmethod'])
def wired_method_builder(request):
    kind = request.param

    def build(wire, *, annotation=object):
        if kind == 'method':
            @wire
            class A:
                def f(self, x):
                    return x

                f.__annotations__['x'] = annotation

        elif kind == 'classmethod':
            @wire
            class A:
                def f(cls, x: annotation):
                    return x

                f.__annotations__['x'] = annotation
                f = classmethod(f)
        else:
            @wire
            class A:
                def f(x: annotation):
                    return x

                f.__annotations__['x'] = annotation
                f = staticmethod(f)
        return A().f

    return build


def test_use_inject_annotation(wire_, wired_method_builder):
    f = wired_method_builder(wire_())
    with pytest.raises(TypeError):
        f()

    f = wired_method_builder(wire_(), annotation=Provide[MyService])
    assert f() is world.get(MyService)


def test_dependencies(wire_, wired_method_builder):
    f = wired_method_builder(wire_(methods=['f'], dependencies=('y',)))
    assert f() is world.get('y')

    f = wired_method_builder(wire_(methods=['f'], dependencies=dict(x='z')))
    assert f() is world.get('z')

    f = wired_method_builder(wire_(methods=['f'], dependencies=dict(y='z')))
    with pytest.raises(TypeError):
        f()

    f = wired_method_builder(wire_(methods=['f'], dependencies=lambda arg: arg.name * 2))
    assert f() is world.get('xx')


@pytest.mark.parametrize('annotation', [object, MyService])
def test_wiring_auto_provide(wire_, wired_method_builder, annotation):
    f = wired_method_builder(wire_(methods=['f']),
                             annotation=annotation)
    with pytest.raises(TypeError):
        f()

    # Boolean
    f = wired_method_builder(wire_(methods=['f'], auto_provide=False),
                             annotation=annotation)
    with pytest.raises(TypeError):
        f()

    f = wired_method_builder(wire_(methods=['f'], auto_provide=True),
                             annotation=annotation)
    if annotation is MyService:
        assert f() is world.get(MyService)
    else:
        with pytest.raises(TypeError):
            f()

    # List
    f = wired_method_builder(wire_(methods=['f'], auto_provide=[MyService]),
                             annotation=annotation)
    if annotation is MyService:
        assert f() is world.get(MyService)
    else:
        with pytest.raises(TypeError):
            f()

    class Unknown:
        pass

    f = wired_method_builder(wire_(methods=['f'], auto_provide=[Unknown]),
                             annotation=annotation)
    with pytest.raises(TypeError):
        f()

    # Function
    f = wired_method_builder(wire_(methods=['f'],
                                   auto_provide=lambda cls: issubclass(cls, MyService)),
                             annotation=annotation)
    if annotation is MyService:
        assert f() is world.get(MyService)
    else:
        with pytest.raises(TypeError):
            f()

    f = wired_method_builder(wire_(methods=['f'], auto_provide=lambda cls: False),
                             annotation=annotation)
    with pytest.raises(TypeError):
        f()


def test_complex_wiring(wire_):
    @wire_(auto_provide=True,
           methods=['g'])
    class A:
        def f(self, x: MyService):
            return x

        def g(self, x: MyService):
            return x

    with pytest.raises(TypeError):
        A().f()

    assert A().g() == world.get(MyService)


def test_class_static_methods(wire_):
    @wire_(methods=['static', 'klass'],
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

    def copy(self, wiring: Wiring):
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


def test_new_old_wiring_wire():
    wiring = Wiring()

    class Dummy:
        pass

    with pytest.raises(TypeError, match=".*class.*"):
        wiring.wire(object())

    with pytest.raises(TypeError, match=".*class.*"):
        wiring.wire(klass=object())

    with pytest.raises(ValueError, match=".*cls.*__klass.*together.*"):
        wiring.wire(Dummy, klass=Dummy)


@pytest.mark.parametrize('type_hints_locals', [None, dict()])
def test_class_in_localns(type_hints_locals):
    wiring = Wiring()

    @dataclass
    class Dummy:
        service: MyService

        @classmethod
        def create(cls, service: MyService = inject.me()) -> Dummy:
            return Dummy(service=service)

    with pytest.raises(NameError, match="Dummy"):
        wiring.wire(klass=Dummy, type_hints_locals=type_hints_locals, class_in_localns=False)

    wiring.wire(klass=Dummy, type_hints_locals=type_hints_locals, class_in_localns=True)
    assert Dummy.create().service is world.get(MyService)


def test_default_class_in_localns(wire_):
    @wire_()
    @dataclass
    class Dummy:
        service: MyService

        @classmethod
        def create(cls, service: MyService = inject.me()) -> Dummy:
            return Dummy(service=service)

    assert Dummy.create().service is world.get(MyService)

    @wire_(ignore_type_hints=True)
    @dataclass
    class Dummy2:
        service: MyService

        @classmethod
        def create(cls, service: MyService = inject.get(MyService)) -> Dummy:
            return Dummy(service=service)

    assert Dummy2.create().service is world.get(MyService)


def test_invalid_class_in_localns():
    class Dummy:
        pass

    with pytest.raises(TypeError, match="class_in_localns"):
        Wiring().wire(klass=Dummy, class_in_localns=object())

    with pytest.raises(ValueError, match="class_in_localns"):
        Wiring(ignore_type_hints=True).wire(klass=Dummy, class_in_localns=True)
