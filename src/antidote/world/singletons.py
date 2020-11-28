from typing import Hashable

from .._internal import API, state


@API.public
def add(dependency: Hashable, instance):
    """
    Declare a singleton dependency with its associated instance.
    """
    state.get_container().add_singletons({dependency: instance})


@API.public
def add_all(dependencies: dict):
    """
    Declare multiple singleton dependencies.

    Args:
        dependencies: Dictionary of dependencies to their associated value.

    """
    state.get_container().add_singletons(dependencies)
