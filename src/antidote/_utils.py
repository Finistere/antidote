import inspect
from collections import abc as c_abc
from typing import (FrozenSet, Iterable, Optional, Callable, Any)

from ._internal import API
from ._internal.wrapper import get_wrapper_injections


@API.private
def validated_parameters(parameters: Optional[Iterable[str]]) -> Optional[FrozenSet[str]]:
    if parameters is None:
        return None

    if not isinstance(parameters, str) and isinstance(parameters, c_abc.Iterable):
        parameters = frozenset(parameters)
        if not parameters:
            return None

        if all(isinstance(p, str) for p in parameters):
            return parameters

    raise TypeError(f"parameters must be an iterable of strings or None, "
                    f"not {type(parameters)}")


@API.private
def validate_method_parameters(method: Callable[..., Any],
                               parameters: Optional[FrozenSet[str]]) -> None:
    if parameters is None:
        return

    try:
        injections = get_wrapper_injections(method)
    except TypeError:
        injections = {}

    signature = inspect.signature(method)
    for param in parameters:
        argument = signature.parameters.get(param)
        if argument is not None and argument.default is not inspect.Parameter.empty:
            raise ValueError(f"Parameter '{param}' cannot have a "
                             f"default value in {method.__name__}().")
        if param in injections:
            raise ValueError(f"Parameter '{param}' cannot have an injection in "
                             f"{method.__name__}().  It currently will be injected with "
                             f"{injections[param]!r}")
