import inspect
import sys
from typing import Any, Callable, Sequence, Tuple

import functools

PY3 = sys.version_info[0] >= 3

if PY3:
    def get_arguments_specification(func):
        # type: (Callable) -> Tuple[Sequence[Tuple[str, bool]], bool, bool]
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
else:
    def get_arguments_specification(func):
        # type: (Any) -> Tuple[Sequence[Tuple[str, bool]], bool, bool]
        # There is no "method" type...
        """
        Extract the name and if a default is set for each argument.
        """
        try:
            argspec = inspect.getargspec(func)
        except TypeError:  # builtin methods or object.__init__
            return tuple(), False, False
        else:
            arguments = []
            first_default = len(argspec.args) - len(argspec.defaults or [])

            if inspect.ismethod(func) and func.__self__ is not None:
                args = argspec.args[1:]
                first_default -= 1
            else:
                args = argspec.args

            for i, name in enumerate(args):
                arguments.append((name, first_default <= i))

            return (
                arguments,
                argspec.varargs is not None,
                argspec.keywords is not None,
            )


def functools_wraps(f):
    # for Python 2
    wrapper_assignments = [
        attr
        for attr in functools.WRAPPER_ASSIGNMENTS
        if hasattr(f, attr)
    ]

    return functools.wraps(f, assigned=wrapper_assignments)
