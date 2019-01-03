import pkg_resources as _pkg_resources

from .core import inject
from .helpers import (attrib, context, factory, new_container, provider, register,
                      resource, wire)
from .providers.service import Build
from .providers.tag import Tag, Tagged, TaggedDependencies

try:
    __version__ = _pkg_resources.get_distribution(__name__).version
except _pkg_resources.DistributionNotFound:  # pragma: no cover
    # package is not installed
    pass

__all__ = [
    'Build',
    'Tag',
    'Tagged',
    'attrib',
    'context',
    'factory',
    'inject',
    'new_container',
    'wire'
]

world = new_container()
