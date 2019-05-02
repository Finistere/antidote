from .core import inject
from .helpers import (factory, implements, LazyConstantsMeta, new_container, provider,
                      register, wire)
from .providers.lazy import LazyCall, LazyMethodCall
from .providers.factory import Build
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
           'new_container',
           'provider',
           'register',
           'Tag',
           'Tagged',
           'TaggedDependencies',
           'wire',
           'world']

world = new_container()
