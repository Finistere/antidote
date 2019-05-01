from .core.exceptions import (AntidoteError, DependencyCycleError,
                              DependencyInstantiationError, DependencyNotFoundError,
                              DuplicateDependencyError)


class DuplicateTagError(AntidoteError):
    """
    A dependency has multiple times the same tag.
    Raised by the :py:class:`~.providers.tag.TagProvider`.
    """


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
    'UndefinedContextError'
]
