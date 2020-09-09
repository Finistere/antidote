from antidote import world
from .helpers import (implementation, factory, implements, inject,
                      LazyConstantsMeta, provider, register, wire)
from .providers.factory import Build
from .providers.lazy import LazyCall, LazyMethodCall
from .providers.tag import Tag, Tagged, TaggedDependencies
from .utils import is_compiled


def __version__() -> str:  # pragma: no cover
    import pkg_resources
    try:
        return pkg_resources.get_distribution(__name__).version
    except pkg_resources.DistributionNotFound:  # pragma: no cover
        # package is not installed
        return ''


__all__ = ['Build',
           'factory',
           'implements',
           'inject',
           'is_compiled',
           'LazyCall',
           'LazyConstantsMeta',
           'LazyMethodCall',
           'provider',
           'register',
           'Tag',
           'Tagged',
           'TaggedDependencies',
           'wire',
           'world']
