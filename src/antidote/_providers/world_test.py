from typing import (Callable, Dict, Hashable, Mapping,
                    Optional,
                    Tuple)

from .._internal import API
from .._internal.utils import debug_repr
from ..core import Container, DependencyDebug, DependencyValue, Provider, Scope


@API.private
class WorldTestProvider(Provider[Hashable]):
    def __init__(self) -> None:
        super().__init__()
        self.__singletons: Dict[Hashable, object] = dict()
        self.__factories: Dict[Hashable,
                               Tuple[Callable[[], object], Optional[Scope]]] = dict()

    def clone(self, keep_singletons_cache: bool) -> 'WorldTestProvider':
        p = WorldTestProvider()
        if keep_singletons_cache:
            p.__singletons = self.__singletons
        p.__factories = self.__factories
        return p

    def exists(self, dependency: Hashable) -> bool:
        return dependency in self.__singletons or dependency in self.__factories

    def debug(self, dependency: Hashable) -> DependencyDebug:
        try:
            value = self.__singletons[dependency]
        except KeyError:
            (factory, scope) = self.__factories[dependency]
            return DependencyDebug(f"Singleton: {debug_repr(dependency)} "
                                   f"-> {factory}",
                                   wired=[factory],
                                   scope=scope)
        else:
            return DependencyDebug(f"Singleton: {debug_repr(dependency)} "
                                   f"-> {value}",
                                   scope=Scope.singleton())

    def provide(self, dependency: Hashable, container: Container) -> DependencyValue:
        try:
            value = self.__singletons[dependency]
        except KeyError:
            (factory, scope) = self.__factories[dependency]
            return DependencyValue(factory(), scope=scope)
        else:
            return DependencyValue(value, scope=Scope.singleton())

    def add_singletons(self, dependencies: Mapping[Hashable, object]) -> None:
        for k, v in dependencies.items():
            self._assert_not_duplicate(k)
        self.__singletons.update(dependencies)

    def add_factory(self,
                    dependency: Hashable,
                    *,
                    factory: Callable[[], object],
                    scope: Optional[Scope]) -> None:
        self._assert_not_duplicate(dependency)
        self.__factories[dependency] = (factory, scope)
