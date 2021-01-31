from typing import Dict, Hashable

from antidote.core import DependencyValue, Provider, Scope


class DummyProvider(Provider):

    def clone(self, keep_singletons_cache: bool) -> Provider:
        return DummyProvider(self.data, self.singleton)

    def __init__(self, data: Dict = None, singleton: bool = True):
        super().__init__()
        self.singleton = singleton
        self.data = data

    def exists(self, dependency: Hashable) -> bool:
        return dependency in self.data

    def provide(self, dependency, container):
        return DependencyValue(self.data[dependency],
                               scope=Scope.singleton() if self.singleton else None)


class DummyFactoryProvider(Provider):

    def clone(self, keep_singletons_cache: bool) -> Provider:
        return DummyFactoryProvider(self.data, self.singleton)

    def __init__(self, data: Dict = None, singleton: bool = True):
        super().__init__()
        self.singleton = singleton
        self.data = data or dict()

    def exists(self, dependency: Hashable) -> bool:
        return dependency in self.data

    def provide(self, dependency, container):
        return DependencyValue(self.data[dependency](container),
                               scope=Scope.singleton() if self.singleton else None)
