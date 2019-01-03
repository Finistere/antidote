from .core.exceptions import (AntidoteError, DependencyCycleError,
                              DependencyInstantiationError, DependencyNotFoundError)


class DuplicateDependencyError(AntidoteError):
    """
    A dependency already exists with the same id.
    *May* be raised by providers.
    """


class DuplicateTagError(AntidoteError):
    """
    A dependency has multiple times the same tag.
    Raised by the TagProvider.
    """


class ResourcePriorityConflict(AntidoteError):
    """
    Two getters having the same namespace have also the same priority.
    Raised by the GetterProvider.
    """


__all__ = [
    'AntidoteError',
    'DependencyCycleError',
    'DependencyInstantiationError',
    'DependencyNotFoundError',
    'DuplicateDependencyError',
    'DuplicateTagError',
    'ResourcePriorityConflict'
]
