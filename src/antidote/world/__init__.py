from typing import Hashable

from . import singletons, test
from .._internal import state
from .._internal.utils import API

# Creates the global container
state.init()


@API.public
def get(dependency: Hashable):
    """
    Returns an instance for the given dependency. All registered providers
    are called sequentially until one returns an instance.  If none is
    found, :py:exc:`~.exceptions.DependencyNotFoundError` is raised.

    Args:
        dependency: Passed on to the registered providers.

    Returns:
        instance for the given dependency
    """
    return state.get_container().get(dependency)


@API.public
def freeze():
    """
    Freezes current :py:class:`~..DependencyContainer`. No additional dependencies
    can be added and singletons cannot be changed anymore.
    """
    state.get_container().freeze()


@API.public
def is_test():
    """
    Whether the current world is a test one or not.
    """
    return state.is_overridden()
