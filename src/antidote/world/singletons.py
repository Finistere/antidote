from typing import Hashable, Dict

from .._internal import state
from .._internal.utils import API


@API.public
def set(dependency: Hashable, obj):
    state.get_container().update_singletons({dependency: obj})


@API.public
def update(dependencies: Dict):
    state.get_container().update_singletons(dependencies)
