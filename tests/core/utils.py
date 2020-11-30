from typing import Dict, Hashable

from antidote.core import DependencyInstance, Provider


class DummyProvider(Provider):
    singleton = True

    def clone(self, keep_singletons_cache: bool) -> Provider:
        return DummyProvider(self.data)

    def __init__(self, data: Dict = None):
        super().__init__()
        self.data = data

    def exists(self, dependency: Hashable) -> bool:
        return dependency in self.data

    def provide(self, dependency, container):
        return DependencyInstance(self.data[dependency],
                                  singleton=self.singleton)


class DummyFactoryProvider(Provider):
    singleton = True

    def clone(self, keep_singletons_cache: bool) -> Provider:
        return DummyFactoryProvider(self.data)

    def __init__(self, data: Dict = None):
        super().__init__()
        self.data = data or dict()

    def exists(self, dependency: Hashable) -> bool:
        return dependency in self.data

    def provide(self, dependency, container):
        return DependencyInstance(self.data[dependency](container),
                                  singleton=self.singleton)
