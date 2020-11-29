from . import world
from .constants import const, Constants
from .core import inject, wire, Wiring
from .factory import factory, Factory
from .implementation import Implementation, implementation
from .lazy import LazyCall, LazyMethodCall
from .service import service, Service
from .tag import Tag, Tagged
from .utils import is_compiled


def __version__() -> str:  # pragma: no cover
    import pkg_resources
    try:
        return pkg_resources.get_distribution(__name__).version
    except pkg_resources.DistributionNotFound:
        # package is not installed
        return ''


__all__ = ['factory',
           'Implementation',
           'inject',
           'is_compiled',
           'LazyCall',
           'LazyMethodCall',
           'service',
           'Tag',
           'Constants',
           'Service',
           'Tagged',
           'wire',
           'world']
