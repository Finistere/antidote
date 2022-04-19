from .injectable import injectable

from ..._internal import API

__all__ = ['register_injectable_provider', 'injectable']


@API.experimental
def register_injectable_provider() -> None:
    from ... import world
    from ._provider import InjectableProvider
    world.provider(InjectableProvider)
