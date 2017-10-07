from .manager import ServiceManager
from .container import Container, Service
from .builder import Builder
from .exceptions import *


manager = ServiceManager()

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
