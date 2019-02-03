import pytest
from pretend import raiser

from antidote._internal.argspec import Argument, Arguments


def f(a: str, b, c: int = 1):
    pass


def g(a: list, *args):
    pass


def h(b=None, **kwargs):
    pass


def k():
    pass


class Dummy:
    def f(self, a: str, b=1, *args, **kwargs):
        pass

    @classmethod
    def g(cls, a):
        pass

    @staticmethod
    def h():
        pass


d = Dummy()


def lazy(dummy: 'Dummy'):
    pass


@pytest.mark.parametrize(
    'func,expected',
    [
        pytest.param(
            f,
            Arguments(
                arguments=tuple([
                    Argument('a', False, str),
                    Argument('b', False, None),
                    Argument('c', True, int),
                ]),
                has_var_positional=False,
                has_var_keyword=False,
            ),
            id='f'
        ),
        pytest.param(
            g,
            Arguments(
                arguments=tuple([
                    Argument('a', False, list),
                ]),
                has_var_positional=True,
                has_var_keyword=False,
            ),
            id='g'
        ),
        pytest.param(
            h,
            Arguments(
                arguments=tuple([
                    Argument('b', True, None),
                ]),
                has_var_positional=False,
                has_var_keyword=True,
            ),
            id='h'
        ),
        pytest.param(
            k,
            Arguments(
                arguments=tuple([]),
                has_var_positional=False,
                has_var_keyword=False,
            ),
            id='k'
        ),
        pytest.param(
            lazy,
            Arguments(
                arguments=tuple([
                    Argument('dummy', False, Dummy),
                ]),
                has_var_positional=False,
                has_var_keyword=False,
            ),
            id='lazy'
        ),
        pytest.param(
            Dummy.f,
            Arguments(
                arguments=tuple([
                    Argument('self', False, None),
                    Argument('a', False, str),
                    Argument('b', True, None),
                ]),
                has_var_positional=True,
                has_var_keyword=True,
            ),
            id='cls.f'
        ),
        pytest.param(
            Dummy.g,
            Arguments(
                arguments=tuple([
                    Argument('a', False, None),
                ]),
                has_var_positional=False,
                has_var_keyword=False,
            ),
            id='cls.g'
        ),
        pytest.param(
            Dummy.h,
            Arguments(
                arguments=tuple([]),
                has_var_positional=False,
                has_var_keyword=False,
            ),
            id='cls.h'
        ),
        pytest.param(
            d.f,
            Arguments(
                arguments=tuple([
                    Argument('a', False, str),
                    Argument('b', True, None),
                ]),
                has_var_positional=True,
                has_var_keyword=True,
            ),
            id='instance.f'
        ),
        pytest.param(
            d.g,
            Arguments(
                arguments=tuple([
                    Argument('a', False, None),
                ]),
                has_var_positional=False,
                has_var_keyword=False,
            ),
            id='instance.g'
        ),
        pytest.param(
            d.h,
            Arguments(
                arguments=tuple([]),
                has_var_positional=False,
                has_var_keyword=False,
            ),
            id='instance.h'
        ),
    ]
)
def test_from_callable(func, expected: Arguments):
    result = Arguments.from_callable(func)
    assert isinstance(result, Arguments)
    assert expected.has_var_positional == result.has_var_positional
    assert expected.has_var_keyword == result.has_var_keyword

    for expected_arg, result_arg in zip(expected, result):
        assert expected_arg.name == result_arg.name
        assert expected_arg.has_default == result_arg.has_default
        assert expected_arg.type_hint == result_arg.type_hint

    for expected_arg in expected:
        assert expected_arg.name in result

        result_arg = result[expected_arg.name]
        assert expected_arg.name == result_arg.name
        assert expected_arg.has_default == result_arg.has_default
        assert expected_arg.type_hint == result_arg.type_hint


@pytest.mark.parametrize(
    'descriptor',
    [staticmethod, classmethod]
)
def test_from_methods(descriptor):
    def f(a, b=None):
        pass

    expected = Arguments.from_callable(f)
    result = Arguments.from_method(descriptor(f))

    for expected_arg, result_arg in zip(expected, result):
        assert expected_arg.name == result_arg.name
        assert expected_arg.has_default == result_arg.has_default
        assert expected_arg.type_hint == result_arg.type_hint


def test_broken_type_hints_cpy353(monkeypatch):
    monkeypatch.setattr('antidote._internal.argspec.get_type_hints', raiser(Exception))
    Arguments.from_callable(k)


def test_magic_methods_arguments():
    arguments = tuple([
        Argument('x', False, int),
        Argument('y', True, str),
        Argument('z', False, float),
    ])
    args = Arguments(
        arguments=arguments,
        has_var_keyword=True,
        has_var_positional=True
    )

    assert 'x' in args
    assert 'unknown' not in args
    assert 3 == len(args)
    assert arguments == tuple(args)
