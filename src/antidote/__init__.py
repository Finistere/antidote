from . import world
from .constants import Constants, const
from .core import (Arg, From, FromArg, Get, Provide, Scope, Wiring, inject, wire)
from .factory import Factory, factory
from .implementation import implementation
from .lazy import LazyCall, LazyMethodCall
from .service import Service, service
from .utils import is_compiled


try:
    from ._internal.scm_version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = ''


__all__ = ['__version__', 'world', 'Get', 'From', 'FromArg', 'Provide',
           'const', 'Constants', 'inject', 'Arg', 'wire', 'Wiring', 'factory',
           'Factory', 'implementation', 'LazyCall', 'LazyMethodCall',
           'service', 'Service', 'is_compiled']
