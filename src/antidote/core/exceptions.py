import inspect
from typing import List


class AntidoteError(Exception):
    """ Base class of all errors of antidote. """

    def __repr__(self):
        return "{}({})".format(type(self).__name__, str(self))


class DuplicateDependencyError(AntidoteError):
    """
    A dependency already exists with the same id.
    *May* be raised by providers.
    """


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

    def __init__(self, stack: List):
        self.stack = stack

    def __str__(self):
        return ' => '.join(map(self._repr, self.stack))

    @staticmethod
    def _repr(obj) -> str:
        if inspect.isclass(obj):
            return "{}.{}".format(obj.__module__, obj.__name__)

        return repr(obj)


class DependencyNotFoundError(AntidoteError):
    """
    The dependency could not be found in the core.
    Raised by the core.
    """

    def __init__(self, dependency):
        self.missing_dependency = dependency

    def __str__(self):
        return repr(self.missing_dependency)
