from .__version__ import __version__
from .container import Instance, DependencyContainer, Dependency
from .exceptions import (
    DependencyCycleError, DependencyDuplicateError, AntidoteError,
    DependencyInstantiationError, DependencyNotFoundError,
    DependencyNotProvidableError
)
from .injector import DependencyInjector
from .manager import DependencyManager

__all__ = [
    'Instance',
    'DependencyContainer',
    'DependencyInjector',
    'DependencyManager',
    'AntidoteError',
    'DependencyNotProvidableError',
    'DependencyNotFoundError',
    'DependencyDuplicateError',
    'DependencyCycleError',
    'DependencyInstantiationError',
    'Dependency',
    'antidote'
]

antidote = DependencyManager()
