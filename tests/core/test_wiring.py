import pytest

from antidote import world
from antidote.core.wiring import Wiring, WithWiringMixin


class Dummy:
    pass


@pytest.fixture(autouse=True)
def new_world():
    with world.test.empty():
        world.singletons.add({'x': object(),
                              'xx': object(),
                              'y': object(),
                              'z': object(),
                              Dummy: Dummy()})
        yield


@pytest.mark.parametrize('kwargs, expectation', [
    (dict(methods=[]), pytest.raises(ValueError, match=".*method.*")),
    (dict(methods=[1]), pytest.raises(ValueError, match="(?i).*method.*")),
    (dict(), pytest.raises(TypeError, match=".*.*")),
    (dict(methods=1), pytest.raises(TypeError, match=".*method.*")),
    (dict(methods=['f'], dependencies=1),
     pytest.raises(TypeError, match=".*dependencies.*")),
    (dict(methods=['f'], use_names=1), pytest.raises(TypeError, match=".*use_names.*")),
    (dict(methods=['f'], use_type_hints=1),
     pytest.raises(TypeError, match=".*use_type_hints.*")),
    (dict(methods=['f'], wire_super=1), pytest.raises(TypeError, match=".*wire_super.*")),
    (dict(methods=['f'], wire_super=['x']),
     pytest.raises(ValueError, match=".*wire_super.*")),
    (dict(methods=['f'], ignore_missing_method=1),
     pytest.raises(TypeError, match=".*ignore_missing_method.*")),
    (dict(methods=['f'], ignore_missing_method=['x']),
     pytest.raises(ValueError, match=".*ignore_missing_method.*"))
])
def test_validation(kwargs, expectation):
    with expectation:
        Wiring(**kwargs)


@pytest.mark.parametrize('kwargs, expected', [
    (dict(methods=['f']), dict()),
    (dict(methods=iter(['f', 'x'])), dict(methods={'f', 'x'})),
    (dict(methods=['f'], use_names=iter(['x'])), dict(use_names={'x'})),
    (dict(methods=['f'], use_type_hints=iter(['x'])), dict(use_type_hints={'x'})),
    (dict(methods=['f'], wire_super=iter(['f'])), dict(wire_super={'f'})),
    (dict(methods=['f'], wire_super=True), dict(wire_super={'f'})),
    (dict(methods=['f'], wire_super=False), dict(wire_super=set())),
    (dict(methods=['f'], ignore_missing_method=True),
     dict(ignore_missing_method={'f'})),
    (dict(methods=['f'], ignore_missing_method=False),
     dict(ignore_missing_method=set())),
    (dict(methods=['f'], ignore_missing_method=iter(['f'])),
     dict(ignore_missing_method={'f'})),
])
def test_init(kwargs, expected):
    result = Wiring(**kwargs)
    expected_methods = expected.get('methods', {'f'})
    assert result.methods == expected_methods
    assert result.wire_super == expected.get('wire_super', set())
    assert result.ignore_missing_method == expected.get('ignore_missing_method', set())
    assert result.dependencies == expected.get('dependencies')
    assert result.use_names == expected.get('use_names')
    assert result.use_type_hints == expected.get('use_type_hints')


def test_wiring_methods():
    wiring = Wiring(methods=['f'])

    @wiring.wire
    class A:
        def f(self, x: Dummy):
            return x

        def g(self, x: Dummy):
            return x

    assert A().f() is world.get(Dummy)
    with pytest.raises(TypeError):
        A().g()


def test_wiring_super_methods():
    class A:
        def f(self, x: Dummy):
            return x

    with pytest.raises(AttributeError, match=".*'f'.*"):
        wiring = Wiring(methods=['f'])

        @wiring.wire
        class X(A):
            pass

    with pytest.raises(AttributeError, match=".*'f'.*"):
        wiring = Wiring(methods=['f'], wire_super=False)

        @wiring.wire
        class Y(A):
            pass

    c_wiring = Wiring(methods=['f'], wire_super=True)

    @c_wiring.wire
    class C(A):
        pass

    assert C().f() is world.get(Dummy)


def test_wiring_dependencies():
    a_wiring = Wiring(methods=['f'], dependencies=('y',))

    @a_wiring.wire
    class A:
        def f(self, x: Dummy):
            return x

    assert A().f() is world.get('y')

    b_wiring = Wiring(methods=['f'], dependencies=dict(x='z'))

    @b_wiring.wire
    class B:
        def f(self, x: Dummy):
            return x

    assert B().f() is world.get('z')

    c_wiring = Wiring(methods=['f'], dependencies="{arg_name}")

    @c_wiring.wire
    class C:
        def f(self, x: Dummy):
            return x

    assert C().f() is world.get('x')

    d_wiring = Wiring(methods=['f'], dependencies=lambda arg: arg.name * 2)

    @d_wiring.wire
    class D:
        def f(self, x: Dummy):
            return x

    assert D().f() is world.get('xx')


def test_wiring_use_names():
    a_wiring = Wiring(methods=['f'])

    @a_wiring.wire
    class A:
        def f(self, y):
            return y

    with pytest.raises(TypeError):
        A().f()

    b_wiring = Wiring(methods=['f'], use_names=False)

    @b_wiring.wire
    class B:
        def f(self, y):
            return y

    with pytest.raises(TypeError):
        B().f()

    c_wiring = Wiring(methods=['f'], use_names=True)

    @c_wiring.wire
    class C:
        def f(self, y):
            return y

    assert C().f() is world.get('y')

    d_wiring = Wiring(methods=['f'], use_names=['y'])

    @d_wiring.wire
    class D:
        def f(self, y):
            return y

    assert D().f() is world.get('y')


def test_wiring_use_type_hints():
    a_wiring = Wiring(methods=['f'])

    @a_wiring.wire
    class A:
        def f(self, y: Dummy):
            return y

    assert A().f() is world.get(Dummy)

    b_wiring = Wiring(methods=['f'], use_type_hints=False)

    @b_wiring.wire
    class B:
        def f(self, y: Dummy):
            return y

    with pytest.raises(TypeError):
        B().f()

    c_wiring = Wiring(methods=['f'], use_type_hints=True)

    @c_wiring.wire
    class C:
        def f(self, y: Dummy):
            return y

    assert C().f() is world.get(Dummy)

    d_wiring = Wiring(methods=['f'], use_type_hints=['y'])

    @d_wiring.wire
    class D:
        def f(self, y: Dummy):
            return y

    assert D().f() is world.get(Dummy)


def test_complex_wiring():
    wiring = Wiring(methods=['f', 'g'],
                    use_names=['x'],
                    wire_super=True)

    class A:
        def g(self, x, y=None):
            return x, y

    @wiring.wire
    class B(A):
        def f(self, x: Dummy):
            return x

    assert B().f() is world.get(Dummy)
    assert B().g() == (world.get('x'), None)


def test_wiring_static_class_method():
    a_wiring = Wiring(methods=['static', 'klass'])

    @a_wiring.wire
    class A:
        @staticmethod
        def static(x: Dummy):
            return x

        @classmethod
        def klass(cls, x: Dummy):
            return cls, x

    assert A.static() is world.get(Dummy)
    assert A.klass() == (A, world.get(Dummy))
    assert A().static() is world.get(Dummy)
    assert A().klass() == (A, world.get(Dummy))

    class B:
        @staticmethod
        def static(x: Dummy):
            return x

        @classmethod
        def klass(cls, x: Dummy):
            return cls, x

    c_wiring = Wiring(methods=['static', 'klass'], wire_super=True)

    @c_wiring.wire
    class C(B):
        pass

    assert C.static() is world.get(Dummy)
    assert C.klass() == (C, world.get(Dummy))
    assert C().static() is world.get(Dummy)
    assert C().klass() == (C, world.get(Dummy))


def test_ignore_missing_method():
    with pytest.raises(AttributeError, match=".*unknown_method.*"):
        wiring = Wiring(methods=['unknown_method'])

        @wiring.wire
        class X:
            pass

    with pytest.raises(AttributeError, match=".*unknown_method.*"):
        wiring = Wiring(methods=['unknown_method'], ignore_missing_method=False)

        @wiring.wire
        class Y:
            pass

    a_wiring = Wiring(methods=['unknown_method'], ignore_missing_method=True)

    @a_wiring.wire
    class A:
        pass

    b_wiring = Wiring(methods=['method', 'maybe_method'],
                      ignore_missing_method=['maybe_method'])

    @b_wiring.wire
    class B:
        def method(self):
            pass

    with pytest.raises(AttributeError, match=".*method.*"):
        @b_wiring.wire
        class C:
            def maybe_method(self):
                pass


def test_unwrap_class_static_methods():
    wiring = Wiring(methods=['static', 'klass'],
                    use_names=True)  # use_names to force injection

    @wiring.wire
    class Dummy:
        @staticmethod
        def static(x):
            pass

        @classmethod
        def klass(cls, x):
            pass

    assert isinstance(Dummy.__dict__['static'], staticmethod)
    assert isinstance(Dummy.__dict__['klass'], classmethod)


@pytest.mark.parametrize('kwargs', [
    dict(methods={'method', 'test'}),
    dict(dependencies="{arg_name}"),
    dict(use_names=True),
    dict(use_type_hints=True),
    dict(wire_super={'method'}),
    dict(ignore_missing_method={'method'})
])
def test_copy(kwargs):
    wiring = Wiring(methods=['method'],
                    dependencies=dict(),
                    use_names=False,
                    use_type_hints=False,
                    wire_super=False,
                    ignore_missing_method=False)
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
    dict(dependencies="{arg_name}"),
    dict(use_names=True),
    dict(use_type_hints=True),
    dict(wire_super={'method'}),
    dict(ignore_missing_method={'method'})
])
def test_with_wiring(kwargs):
    conf = DummyConf(Wiring(methods=['method'],
                            dependencies=dict(),
                            use_names=False,
                            use_type_hints=False,
                            wire_super=False,
                            ignore_missing_method=False))
    copy = conf.with_wiring(**kwargs)
    for key, value in kwargs.items():
        assert getattr(copy.wiring, key) == value

    kwargs.setdefault('methods', {'method'})
    copy = DummyConf().with_wiring(**kwargs)
    for key, value in kwargs.items():
        assert getattr(copy.wiring, key) == value


def test_invalid_with_wiring():
    with pytest.raises(TypeError):
        DummyConf().with_wiring()
