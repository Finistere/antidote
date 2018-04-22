import inspect
from typing import Callable, Sequence, Tuple

ArgSpecType = Tuple[Sequence[Tuple[str, bool]], bool, bool]


def get_arguments_specification(func: Callable) -> ArgSpecType:
    """
    Extract the name and if a default is set for each argument.
    """
    arguments = []
    has_var_positional = False
    has_var_keyword = False

    for name, parameter in inspect.signature(func).parameters.items():
        if parameter.kind is parameter.VAR_POSITIONAL:
            has_var_positional = True
            continue

        if parameter.kind is parameter.VAR_KEYWORD:
            has_var_keyword = True
            continue

        arguments.append((name,
                          parameter.default is not parameter.empty))

    return arguments, has_var_positional, has_var_keyword
