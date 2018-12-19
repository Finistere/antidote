import inspect
from typing import List


class AntidoteError(Exception):
    """ Base class of all errors of antidote. """


class UndefinedContainerError(AntidoteError):
    """ Raised whenever injection is tried without container """


class DuplicateDependencyError(AntidoteError):
    """
    A dependency already exists with the same id.
    *May* be raised by providers.
    """


class DependencyInstantiationError(AntidoteError):
    """
    The dependency could not be instantiated.
    Raised by the container.
    """


class DependencyCycleError(AntidoteError):
    """
    A dependency cycle is found.
    Raised by the container.
    """

    def __init__(self, stack: List):
        self.stack = stack

    def __repr__(self):
        return "{}({})".format(
            type(self).__name__,
            ' => '.join(map(self._repr, self.stack))
        )

    @staticmethod
    def _repr(obj) -> str:
        if inspect.isclass(obj):
            return "{}.{}".format(obj.__module__, obj.__name__)

        return repr(obj)


class DependencyNotProvidableError(AntidoteError):
    """
    The dependency could not be provided.
    Raised by providers.
    """


class DependencyNotFoundError(AntidoteError):
    """
    The dependency could not be found in the container.
    Raised by the container.
    """


class DuplicateTagError(AntidoteError):
    """
    A dependency has multiple times the same tag.
    Raised by the TagProvider.
    """


class GetterNamespaceConflict(AntidoteError):
    """
    At least two namespaces conflict with each other.
    Raised by the GetterProvider.
    """
