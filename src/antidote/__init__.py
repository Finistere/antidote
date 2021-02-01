from . import world
from .constants import Constants, const
from .core import (Arg, From, FromArg, Get, Provide, Scope, Wiring, inject, wire)
from .factory import Factory, factory
from .implementation import implementation
from .lazy import LazyCall, LazyMethodCall
from .service import Service, service
from .tag import Tag, Tagged
from .utils import is_compiled


def __version__() -> str:  # pragma: no cover
    try:
        from ._internal.scm_version import version
        return str(version)
    except ImportError:
        return ''


__all__ = ['world', 'Get', 'From', 'FromArg', 'Provide',
           'const', 'Constants', 'inject', 'Arg', 'wire', 'Wiring', 'factory',
           'Factory', 'implementation', 'LazyCall', 'LazyMethodCall',
           'service', 'Service', 'Tag', 'Tagged', 'is_compiled']
