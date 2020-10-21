from . import world
from .core import inject, wire, Wiring
from .helpers import (const, Constants, factory, Factory, implementation, implements,
                      LazyCall, LazyMethodCall, service, Service)
from .providers.tag import Tag, Tagged
from .utils import is_compiled


def __version__() -> str:  # pragma: no cover
    import pkg_resources
    try:
        return pkg_resources.get_distribution(__name__).version
    except pkg_resources.DistributionNotFound:  # pragma: no cover
        # package is not installed
        return ''


__all__ = ['factory',
           'implements',
           'inject',
           'is_compiled',
           'LazyCall',
           'LazyMethodCall',
           'service',
           'Tag',
           'Tagged',
           'wire',
           'world']
