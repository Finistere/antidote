from typing import Any, Callable, TypeVar

from ..container import Dependency
from ..exceptions import DependencyNotProvidableError

T = TypeVar('T')


class ParameterProvider:
    """
    Provider managing constant parameters like configuration.
    """

    def __init__(self):
        self._parameter_getter_couples = []

    def __repr__(self):
        return "{}(parameter_getter_couples={!r})".format(
            type(self).__name__,
            tuple(param for param, _ in self._parameter_getter_couples)
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
            A :py:class:`~.container.Dependency` wrapping the built dependency.
        """
        for parameters, getter in self._parameter_getter_couples:
            try:
                param = getter(parameters, dependency_id)
            except LookupError:
                pass
            else:
                if coerce is not None:
                    param = coerce(param)

                return Dependency(param, singleton=True)

        raise DependencyNotProvidableError(dependency_id)

    def register(self, parameters: T, getter: Callable[[T, Any], Any]):
        """
        Register parameters with its parser.

        Args:
            getter: Function used to retrieve a requested dependency from the
                parameters. It must have similar signature to
                :py:func:`~operator.getitem` accepting as first argument
                the object from which to retrieve the data and as second the
                key.
            parameters: Object containing the parameters, usually a mapping.

        """
        self._parameter_getter_couples.append((parameters, getter))
