from . import world
from .constants import const, Constants
from .core import Arg, From, FromArg, Get, inject, Inject, Provide, Scope, wire, Wiring
from .factory import Factory, factory
from .implementation import implementation
from .lazy import LazyCall, LazyMethodCall
from .service import ABCService, Service, service
from .utils import is_compiled
from .extension.predicates import interface, implements

try:
    from ._internal.scm_version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = ''

__all__ = ['__version__', 'world', 'Get', 'From', 'FromArg', 'Provide', 'Inject',
           'const', 'Constants', 'constants', 'inject', 'Arg', 'wire', 'Wiring', 'factory',
           'Factory', 'implementation', 'LazyCall', 'LazyMethodCall',
           'service', 'Scope', 'Service', 'ABCService', 'is_compiled']
