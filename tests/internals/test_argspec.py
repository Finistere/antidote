import pytest

from antidote._internal.argspec import Argument, Arguments, \
    get_arguments_specification


def f(a, b, c=1):
    pass


def g(a, *args):
    pass


def h(b=None, **kwargs):
    pass


def k():
    pass


class Dummy:
    def f(self, a, b=1, *args, **kwargs):
        pass

    @classmethod
    def g(cls, a):
        pass

    @staticmethod
    def h():
        pass


d = Dummy()


@pytest.mark.parametrize(
    'func,expected',
    [
        pytest.param(
            f,
            Arguments(
                arguments=tuple([
                    Argument('a', False),
                    Argument('b', False),
                    Argument('c', True),
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
                    Argument('a', False),
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
                    Argument('b', True),
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
            Dummy.f,
            Arguments(
                arguments=tuple([
                    Argument('self', False),
                    Argument('a', False),
                    Argument('b', True),
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
                    Argument('a', False),
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
                    Argument('a', False),
                    Argument('b', True),
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
                    Argument('a', False),
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
def test_arg_spec(func, expected: Arguments):
    result = get_arguments_specification(func)
    assert isinstance(result, Arguments)
    assert expected.has_var_positional == result.has_var_positional
    assert expected.has_var_keyword == result.has_var_keyword

    for expected_arg, result_arg in zip(expected.arguments, result.arguments):
        assert expected_arg.name == result_arg.name
        assert expected_arg.has_default == result_arg.has_default
