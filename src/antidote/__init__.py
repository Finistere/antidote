from pkg_resources import DistributionNotFound, get_distribution

from .container import Dependency, DependencyContainer, Instance
from .exceptions import (AntidoteError, DependencyCycleError, DependencyDuplicateError,
                         DependencyInstantiationError, DependencyNotFoundError,
                         DependencyNotProvidableError)
from .injector import DependencyInjector
from .manager import DependencyManager
from .providers.factories import Build
from .providers.tags import Tag, Tagged, TaggedDependencies

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:  # pragma: no cover
    # package is not installed
    pass

__all__ = [
    'Build',
    'Instance',
    'DependencyContainer',
    'DependencyInjector',
    'DependencyManager',
    'AntidoteError',
    'DependencyNotProvidableError',
    'DependencyNotFoundError',
    'DependencyDuplicateError',
    'DependencyCycleError',
    'DependencyInstantiationError',
    'Dependency',
    'Tag',
    'Tagged',
    'TaggedDependencies',
    'antidote'
]

antidote = DependencyManager()
