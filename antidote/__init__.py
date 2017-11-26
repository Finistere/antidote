from .manager import DependencyManager
from .container import (
    DependencyContainer, DependencyFactory,
    DependencyNotFoundError, DependencyCycleError, DependencyDuplicateError,
    DependencyInstantiationError
)
from .injector import DependencyInjector
from .exceptions import DependencyError

from .__version__ import (
    __title__, __description__, __url__, __version__, __author__, __license__
)

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
