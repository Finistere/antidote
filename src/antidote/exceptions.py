from ._internal import API
from .core.exceptions import (AntidoteError, DependencyCycleError,
                              DependencyInstantiationError, DependencyNotFoundError,
                              DuplicateDependencyError, FrozenContainerError,
                              FrozenWorldError)
from ._extension.providers import DuplicateTagError


@API.public
class UndefinedContextError(AntidoteError):
    """
    A context does not have any target associated.
    Raised by the :py:class:`~.providers.indirect.IndirectProvider`.
    """


__all__ = [
    'AntidoteError',
    'DependencyCycleError',
    'DependencyInstantiationError',
    'DependencyNotFoundError',
    'DuplicateDependencyError',
    'DuplicateTagError',
    'UndefinedContextError',
    'FrozenWorldError',
    'FrozenContainerError'
]
