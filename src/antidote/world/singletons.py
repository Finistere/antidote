from typing import Hashable

from .._internal import API, state


@API.public
def set(dependency: Hashable, instance):
    """
    Declare a singleton dependency with its associated instance.
    """
    state.get_container().update_singletons({dependency: instance})


@API.public
def update(dependencies: dict):
    """
    Declare multiple singleton dependencies.

    Args:
        dependencies: Dictionary of dependencies to their associated value.

    """
    state.get_container().update_singletons(dependencies)
