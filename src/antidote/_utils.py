import inspect
from typing import Callable, Sequence


class SlotReprMixin:
    __slots__ = ()

    def __repr__(self):
        return "{type}({slots})".format(
            type=type(self).__name__,
            slots=', '.join((
                '{}={!r}'.format(name, getattr(self, name))
                for name in self.__slots__
            ))
        )


class Argument(SlotReprMixin):
    __slots__ = ('name', 'has_default')

    def __init__(self, name: str, has_default: bool):
        self.name = name
        self.has_default = has_default


class ArgumentSpecification(SlotReprMixin):
    __slots__ = ('arguments', 'has_var_positional', 'has_var_keyword')

    def __init__(self,
                 arguments: Sequence[Argument],
                 has_var_positional: bool,
                 has_var_keyword: bool):
        self.arguments = arguments
        self.has_var_positional = has_var_positional
        self.has_var_keyword = has_var_keyword


def get_arguments_specification(func: Callable) -> ArgumentSpecification:
    """
    Extract the name and if a default is set for each argument.
    """
    arguments = []
    has_var_positional = False
    has_var_keyword = False

    for name, parameter in inspect.signature(func).parameters.items():
        if parameter.kind is parameter.VAR_POSITIONAL:
            has_var_positional = True
        elif parameter.kind is parameter.VAR_KEYWORD:
            has_var_keyword = True
        else:
            arguments.append(Argument(
                name=name,
                has_default=parameter.default is not parameter.empty
            ))

    return ArgumentSpecification(arguments=tuple(arguments),
                                 has_var_positional=has_var_positional,
                                 has_var_keyword=has_var_keyword)
