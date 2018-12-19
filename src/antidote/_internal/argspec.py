import inspect
from typing import Callable, Sequence

from .utils import SlotReprMixin


class Argument(SlotReprMixin):
    def __init__(self, name: str, has_default: bool):
        self.name = name
        self.has_default = has_default


class Arguments:
    def __init__(self,
                 arguments: Sequence[Argument],
                 has_var_positional: bool,
                 has_var_keyword: bool):
        self.arguments = arguments
        self.has_var_positional = has_var_positional
        self.has_var_keyword = has_var_keyword

    def __iter__(self):
        return iter(self.arguments)


def get_arguments_specification(func: Callable) -> Arguments:
    """
    Extract for each argument its name and if a default is set.
    Whether the function accepts *args and/or **kwargs is also extracted.

    Currently only used in the injection to determine all arguments which may
    need injection.
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

    return Arguments(arguments=tuple(arguments),
                     has_var_positional=has_var_positional,
                     has_var_keyword=has_var_keyword)
