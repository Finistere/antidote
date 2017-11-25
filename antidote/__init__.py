from .manager import DependencyManager
from .container import DependencyContainer, DependencyFactory, \
    DependencyNotFoundError, DependencyCycleError, DependencyDuplicateError, \
    DependencyInstantiationError
from .injector import DependencyInjector
from .exception import DependencyError


__version__ = '0.1'

__all__ = [
    'DependencyContainer',
    'DependencyFactory',
    'DependencyInjector',
    'DependencyManager',
    'DependencyError',
    'DependencyNotFoundError',
    'DependencyDuplicateError',
    'DependencyCycleError',
    'DependencyInstantiationError'
]


antidote = DependencyManager()
