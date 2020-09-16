from typing import Dict, Hashable

from .._internal import API, state


@API.public
def set(dependency: Hashable, obj):
    state.get_container().update_singletons({dependency: obj})


@API.public
def update(dependencies: Dict):
    state.get_container().update_singletons(dependencies)
