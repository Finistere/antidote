import functools
from operator import getitem
from typing import Callable, Mapping, Iterable, Any

from ..container import Dependency
from ..exceptions import DependencyNotProvidableError


class ParameterProvider(object):
    """
    Provider used for for parameters and configuration. Dependency ids are
    converted by parsers to a key for their associated mapping.
    """

    def __init__(self):
        self._parameter_parser_couples = []

    def __repr__(self):
        return "{}(parameter_parser={!r})".format(
            type(self).__name__,
            tuple(param for param, _ in self._parameter_parser_couples)
        )

    def __antidote_provide__(self, dependency_id, type=None, *args, **kwargs):
        # type: (Any, type, *Any, **Any) -> Dependency
        """
        Provide the parameter associated with the dependency_id.

        Args:
            dependency_id: ID of the dependency
            type (optional): If specified, the returned parameter is casted to
                this type.

        Returns:
            Dependency: The found parameter wrapped with
                :py:class:`~.container.Dependency`
        """
        for parameters, parser in self._parameter_parser_couples:
            keys = parser(dependency_id)
            if keys is not None:
                try:
                    param = rgetitem(parameters, keys)
                except (KeyError, TypeError):
                    pass
                else:
                    if type is not None:
                        param = type(param)

                    return Dependency(param, singleton=True)

        raise DependencyNotProvidableError(dependency_id)

    def register(self, parameters, parser):
        # type: (Mapping, Callable[..., Iterable]) -> None
        """
        Register parameters with its parser.

        Args:
            parser (callable): Parse a dependency_id to an iterable of keys.
                The iterable will be used to retrieve the parameter from the
                associated mapping recursively.
            parameters (mapping): Mapping of parameters.

        """
        self._parameter_parser_couples.append((parameters, parser))


def rgetitem(obj, items):
    # type: (Mapping, Iterable) -> Any
    """
    Recursively retrieve an item from an nested mapping.

    Args:
        obj: Nested mapping.
        items: Iterable of keys.

    Returns:
        The retrieved item.
    """
    return functools.reduce(getitem, items, obj)
