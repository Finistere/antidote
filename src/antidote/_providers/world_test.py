from __future__ import annotations

from typing import Callable, Dict, Mapping, Optional, Tuple

from .._internal import API
from .._internal.utils import debug_repr
from ..core import Container, DependencyDebug, DependencyValue, Provider, Scope


@API.private
class WorldTestProvider(Provider[object]):
    def __init__(self) -> None:
        super().__init__()
        self.__singletons: Dict[object, object] = dict()
        self.__factories: Dict[object, Tuple[Callable[[], object], Optional[Scope]]] = dict()

    def clone(self, keep_singletons_cache: bool) -> WorldTestProvider:
        p = WorldTestProvider()
        if keep_singletons_cache:
            p.__singletons = self.__singletons
        p.__factories = self.__factories
        return p

    def exists(self, dependency: object) -> bool:
        return dependency in self.__singletons or dependency in self.__factories

    def debug(self, dependency: object) -> DependencyDebug:
        try:
            value = self.__singletons[dependency]
        except KeyError:
            (factory, scope) = self.__factories[dependency]
            return DependencyDebug(
                f"Singleton: {debug_repr(dependency)} -> {factory}",
                wired=[factory],
                scope=scope,
            )
        else:
            return DependencyDebug(
                f"Singleton: {debug_repr(dependency)} -> {value}", scope=Scope.singleton()
            )

    def provide(self, dependency: object, container: Container) -> DependencyValue:
        try:
            value = self.__singletons[dependency]
        except KeyError:
            (factory, scope) = self.__factories[dependency]
            return DependencyValue(factory(), scope=scope)
        else:
            return DependencyValue(value, scope=Scope.singleton())

    def add_singletons(self, dependencies: Mapping[object, object]) -> None:
        for k in dependencies.keys():
            self._assert_not_duplicate(k)
        self.__singletons.update(dependencies)

    def add_factory(
        self, dependency: object, *, factory: Callable[[], object], scope: Optional[Scope]
    ) -> None:
        self._assert_not_duplicate(dependency)
        self.__factories[dependency] = (factory, scope)
