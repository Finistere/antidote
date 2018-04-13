from typing import Callable

from ..container import Dependency
from ..exceptions import DependencyNotProvidableError


class ParameterProvider:
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

    def __antidote_provide__(self, dependency_id, coerce: type = None, *args,
                             **kwargs) -> Dependency:
        """
        Provide the parameter associated with the dependency_id.

        Args:
            dependency_id: ID of the dependency
            coerce: If specified, the returned parameter is casted to this
                type.

        Returns:
            Dependency: The found parameter wrapped with
                :py:class:`~.container.Dependency`
        """
        for parameters, getter in self._parameter_parser_couples:
            try:
                param = getter(parameters, dependency_id)
            except LookupError:
                pass
            else:
                if coerce is not None:
                    param = coerce(param)

                return Dependency(param, singleton=True)

        raise DependencyNotProvidableError(dependency_id)

    def register(self, parameters, getter: Callable):
        """
        Register parameters with its parser.

        Args:
            getter: Parse a dependency_id to an iterable of keys. The iterable
                will be used to retrieve the parameter from the associated
                mapping recursively.
            parameters: Mapping of parameters.

        """
        self._parameter_parser_couples.append((parameters, getter))
