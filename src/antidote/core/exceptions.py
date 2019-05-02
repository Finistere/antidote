import inspect
from typing import Any, Hashable, List


class AntidoteError(Exception):
    """ Base class of all errors of antidote. """

    def __repr__(self):
        return "{}({})".format(type(self).__name__, str(self))


class DuplicateDependencyError(AntidoteError):
    """
    A dependency already exists with the same id.
    *May* be raised by providers.
    """

    def __init__(self, dependency: Hashable, existing_definition: Any):
        self.dependency = dependency
        self.existing_definition = existing_definition

    def __repr__(self):
        return ("DuplicateDependencyError(dependency={!r}, "
                "existing_definition={!r})").format(
            self.dependency, self.existing_definition
        )

    def __str__(self):
        return "The dependency {} already exists. It points to {}.".format(
            self.dependency,
            self.existing_definition
        )


class DependencyInstantiationError(AntidoteError):
    """
    The dependency could not be instantiated.
    Raised by the core.
    """


class DependencyCycleError(AntidoteError):
    """
    A dependency cycle is found.
    Raised by the core.
    """

    def __init__(self, dependencies: List):
        self.dependencies = dependencies

    def __str__(self):
        return ' => '.join(map(self._repr, self.dependencies))

    @staticmethod
    def _repr(dependency: Hashable) -> str:
        if inspect.isclass(dependency):
            return "{}.{}".format(dependency.__module__,
                                  getattr(dependency, '__name__', dependency))

        return repr(dependency)


class DependencyNotFoundError(AntidoteError):
    """
    The dependency could not be found in the core.
    Raised by the core.
    """

    def __init__(self, dependency: Hashable):
        self.missing_dependency = dependency

    def __str__(self):
        return repr(self.missing_dependency)
