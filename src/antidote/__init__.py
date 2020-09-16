from . import world
from .core import inject, wire, Wiring
from .helpers import (const, factory, Factory, implementation, implements, Constants,
                      register, Service, LazyCall, LazyMethodCall)
from .providers.tag import Tag, TaggedDependencies
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
           'register',
           'Tag',
           'TaggedDependencies',
           'wire',
           'world']

