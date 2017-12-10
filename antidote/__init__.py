from .container import DependencyContainer, Dependency
from .injection import DependencyInjector
from .manager import DependencyManager
from .exceptions import *

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

_manager = DependencyManager()

world = _manager.container
injector = _manager.injector
inject = _manager.inject
register = _manager.register
factory = _manager.factory
wire = _manager.wire
attrib = _manager.attrib
provider = _manager.provider


def set(param, value):
    if param not in {'auto_wire', 'mapping', 'use_names'}:
        raise ValueError("Only the parameters 'auto_wire', 'mapping' "
                         "and 'use_names' can be changed.")
    setattr(_manager, param, value)
