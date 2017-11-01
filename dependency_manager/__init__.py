from .manager import DependencyManager
from .container import DependencyContainer, DependencyFactory
from .injector import DependencyInjector
from .exceptions import *


__version__ = '0.1'

__all__ = [
    'DependencyContainer',
    'DependencyFactory',
    'DependencyInjector',
    'DependencyManager',
    'DependencyNotFoundError',
    'DuplicateDependencyError',
    'DependencyInstantiationError'
]


manager = DependencyManager()

container = manager.container
builder = manager.injector
inject = manager.inject
provider = manager.provider
register = manager.register
wire = manager.wire

try:
    import attr
except ImportError:
    pass
else:
    attrib = manager.attrib
