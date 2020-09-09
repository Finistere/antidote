import inspect
from typing import Any, Hashable, List

from .._internal.utils import API


@API.public
class AntidoteError(Exception):
    """ Base class of all errors of antidote. """

    def __repr__(self):
        return f"{type(self).__name__}({self})"


@API.public
class DuplicateDependencyError(AntidoteError):
    """
    A dependency already exists with the same id.
    *May* be raised by providers.
    """

    def __init__(self, dependency: Hashable, existing_definition: Any):
        self.dependency = dependency
        self.existing_definition = existing_definition

    def __repr__(self):
        return f"DuplicateDependencyError(dependency={self.dependency!r}, " \
               f"existing_definition={self.existing_definition!r})"

    def __str__(self):
        return f"The dependency {self.dependency} already exists. " \
               f"It points to {self.existing_definition}."


@API.public
class DependencyInstantiationError(AntidoteError):
    """
    The dependency could not be instantiated.
    """


@API.public
class DependencyCycleError(AntidoteError):
    """
    A dependency cycle is found.
    """

    def __init__(self, dependencies: List):
        self.dependencies = dependencies

    def __str__(self):
        return ' => '.join(map(self._repr, self.dependencies))

    @staticmethod
    def _repr(dependency: Hashable) -> str:
        if inspect.isclass(dependency):
            return f"{dependency.__module__}" \
                   f".{getattr(dependency, '__name__', dependency)}"

        return repr(dependency)


@API.public
class DependencyNotFoundError(AntidoteError):
    """
    The dependency could not be found.
    """

    def __init__(self, dependency: Hashable):
        self.missing_dependency = dependency

    def __str__(self):
        return repr(self.missing_dependency)


@API.public
class FrozenWorldError(AntidoteError):
    """
    The DependencyContainer and its provider are already frozen, dependencies
    cannot be changed anymore.
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message
