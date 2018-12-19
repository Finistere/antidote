import typing as _t

import pkg_resources as _pkg_resources

from .container import Dependency, DependencyContainer, Instance, Provider
from .exceptions import (AntidoteError, DependencyCycleError,
                         DependencyInstantiationError, DependencyNotFoundError,
                         DependencyNotProvidableError, DuplicateDependencyError)
from .helpers import attrib, context, factory, getter, provider, register, new_container
from .injection import inject
from .providers import FactoryProvider, GetterProvider, TagProvider
from .providers.factory import Build
from .providers.tags import Tag, Tagged, TaggedDependencies

try:
    __version__ = _pkg_resources.get_distribution(__name__).version
except _pkg_resources.DistributionNotFound:  # pragma: no cover
    # package is not installed
    pass

__all__ = [
    'Build',
    'inject',
    'Instance',
    'DependencyContainer',
    'AntidoteError',
    'DependencyNotProvidableError',
    'DependencyNotFoundError',
    'DuplicateDependencyError',
    'DependencyCycleError',
    'DependencyInstantiationError',
    'Dependency',
    'FactoryProvider',
    'GetterProvider',
    'Tag',
    'Tagged',
    'TaggedDependencies',
    'TagProvider',
    'register',
    'factory',
    'getter',
    'provider',
    'attrib',
    'context'
]

global_container = None  # type: _t.Optional[DependencyContainer]
