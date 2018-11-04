import pytest

from antidote._utils import Argument, ArgumentSpecification, SlotReprMixin, \
    get_arguments_specification


class DummySlot(SlotReprMixin):
    __slots__ = ('test', 'value')

    def __init__(self, test, value):
        self.test = test
        self.value = value


def test_slot_repr_mixin():
    assert repr(DummySlot(1, 'test')) == "DummySlot(test=1, value='test')"


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
            ArgumentSpecification(
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
            ArgumentSpecification(
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
            ArgumentSpecification(
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
            ArgumentSpecification(
                arguments=tuple([]),
                has_var_positional=False,
                has_var_keyword=False,
            ),
            id='k'
        ),
        pytest.param(
            Dummy.f,
            ArgumentSpecification(
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
            ArgumentSpecification(
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
            ArgumentSpecification(
                arguments=tuple([]),
                has_var_positional=False,
                has_var_keyword=False,
            ),
            id='cls.h'
        ),
        pytest.param(
            d.f,
            ArgumentSpecification(
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
            ArgumentSpecification(
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
            ArgumentSpecification(
                arguments=tuple([]),
                has_var_positional=False,
                has_var_keyword=False,
            ),
            id='instance.h'
        ),
    ]
)
def test_arg_spec(func, expected: ArgumentSpecification):
    result = get_arguments_specification(func)
    assert isinstance(result, ArgumentSpecification)
    assert expected.has_var_positional == result.has_var_positional
    assert expected.has_var_keyword == result.has_var_keyword

    for expected_arg, result_arg in zip(expected.arguments, result.arguments):
        assert expected_arg.name == result_arg.name
        assert expected_arg.has_default == result_arg.has_default
