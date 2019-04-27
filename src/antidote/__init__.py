from ._internal.utils import is_compiled
from .core import inject
from .helpers import (factory, LazyConfigurationMeta, new_container, provider, register,
                      wire)
from .providers.lazy import LazyCall, LazyMethodCall
from .providers.service import Build
from .providers.tag import Tag, Tagged, TaggedDependencies


def __version__():  # pragma: no cover
    import pkg_resources as _pkg_resources
    try:
        return _pkg_resources.get_distribution(__name__).version
    except _pkg_resources.DistributionNotFound:  # pragma: no cover
        # package is not installed
        pass


__all__ = [
    'Build',
    'LazyCall',
    'LazyMethodCall',
    'LazyConfigurationMeta',
    'Tag',
    'Tagged',
    'factory',
    'inject',
    'new_container',
    'wire'
]

world = new_container()
