"""
Utilities used by world, mostly for syntactic sugar.
"""
from __future__ import annotations

from typing import Any, Callable, cast, final, Hashable, List, Type, TypeVar

from .meta import FinalMeta
from .. import API
from ...core.container import (DependencyContainer, DependencyInstance,
                               RawDependencyProvider)
from ...core.utils import Dependency

T = TypeVar('T')


@API.private
@final
class WorldGet(metaclass=FinalMeta):
    def __call__(self, dependency: Hashable) -> Any:
        from ..state import get_container
        return get_container().get(dependency)

    def __getitem__(self, tpe: Type[T]) -> Callable[[Hashable], T]:
        def f(dependency: Hashable = None) -> T:
            from ..state import get_container
            if dependency is None:
                dependency = tpe
            return cast(T, get_container().get(dependency))

        return f


@API.private
@final
class WorldLazy(metaclass=FinalMeta):
    def __call__(self, dependency: Hashable) -> Dependency[Any]:
        return Dependency(dependency)

    def __getitem__(self, tpe: Type[T]) -> Callable[[Hashable], Dependency[T]]:
        def f(dependency: Hashable = None) -> Dependency[T]:
            if dependency is None:
                dependency = tpe
            return Dependency(dependency)

        return f


@API.private
def new_container():
    """ default new container in Antidote """

    from ...core.container import RawDependencyContainer
    from ...providers import (LazyProvider, ServiceProvider, TagProvider,
                              IndirectProvider, FactoryProvider)

    container = RawDependencyContainer()
    container.register_provider(FactoryProvider)
    container.register_provider(ServiceProvider)
    container.register_provider(LazyProvider)
    container.register_provider(IndirectProvider)
    container.register_provider(TagProvider)

    return container


@API.private
@final
class ProviderCollection(RawDependencyProvider, metaclass=FinalMeta):
    """ Utility class used for creating an overridable world """

    def __init__(self, providers: List[RawDependencyProvider] = None):
        super().__init__()
        self.__providers = providers or list()

    def provide(self,
                dependency: Hashable,
                container: DependencyContainer) -> DependencyInstance:
        for provider in self.__providers:
            dependency_instance = provider.provide(dependency, container)
            if dependency_instance is not None:
                return dependency_instance

    def set_providers(self, providers: List[RawDependencyProvider]):
        self.__providers = providers

    def clone(self, keep_singletons_cache: bool) -> ProviderCollection:
        return ProviderCollection([p.clone(keep_singletons_cache)
                                   for p in self.__providers])
