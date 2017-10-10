from .manager import ServiceManager
from .container import Container, Service
from .builder import Builder
from .exceptions import *


__all__ = [
    'Container',
    'Service',
    'Builder',
    'ServiceManager',
    'UnregisteredServiceError',
    'DuplicateServiceError',
    'ServiceInstantiationError'
]


manager = ServiceManager()

container = manager.container
builder = manager.builder
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
