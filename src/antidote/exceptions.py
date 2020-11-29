from ._extension.providers import DuplicateTagError
from .core.exceptions import (AntidoteError, DependencyCycleError,
                              DependencyInstantiationError, DependencyNotFoundError,
                              DuplicateDependencyError, FrozenContainerError,
                              FrozenWorldError)

__all__ = [
    'AntidoteError',
    'DependencyCycleError',
    'DependencyInstantiationError',
    'DependencyNotFoundError',
    'DuplicateDependencyError',
    'FrozenContainerError',
    'FrozenWorldError',
    'DuplicateTagError'
]
