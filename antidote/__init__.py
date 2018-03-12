from .container import DependencyContainer, Dependency
from .injector import DependencyInjector
from .manager import DependencyManager
from .exceptions import (
    DependencyError, DependencyNotFoundError, DependencyNotProvidableError,
    DependencyDuplicateError, DependencyCycleError,
    DependencyInstantiationError
)

from .__version__ import __version__


__all__ = [
    'Dependency',
    'DependencyContainer',
    'DependencyInjector',
    'DependencyManager',
    'DependencyError',
    'DependencyNotProvidableError',
    'DependencyNotFoundError',
    'DependencyDuplicateError',
    'DependencyCycleError',
    'DependencyInstantiationError'
]

antidote = DependencyManager()
