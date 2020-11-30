"""
Utilities used by world, mostly for syntactic sugar.
"""
from typing import Any, Callable, cast, Type, TypeVar

from .meta import FinalMeta
from ..._compatibility.typing import final
from ..._internal import API
from ...core.container import RawContainer
from ...core.utils import Dependency

T = TypeVar('T')


@API.private
@final
class WorldGet(metaclass=FinalMeta):
    def __call__(self, dependency: object) -> Any:
        from ..state import get_container
        return get_container().get(dependency)

    def __getitem__(self, tpe: Type[T]) -> Callable[[object], T]:
        def f(dependency=None) -> T:
            from ..state import get_container
            if dependency is None:
                dependency = tpe
            return cast(T, get_container().get(dependency))

        return f


@API.private
@final
class WorldLazy(metaclass=FinalMeta):
    def __call__(self, dependency: object) -> Dependency[Any]:
        return Dependency(dependency)

    def __getitem__(self, tpe: Type[T]) -> Callable[[object], Dependency[T]]:
        def f(dependency=None) -> Dependency[T]:
            if dependency is None:
                dependency = tpe
            return Dependency(dependency)

        return f


@API.private
def new_container():
    """ default new container in Antidote """

    from ..._providers import (LazyProvider, ServiceProvider, TagProvider,
                               IndirectProvider, FactoryProvider)

    container = RawContainer()
    container.add_provider(FactoryProvider)
    container.add_provider(ServiceProvider)
    container.add_provider(LazyProvider)
    container.add_provider(IndirectProvider)
    container.add_provider(TagProvider)

    return container
