from typing import Dict

from antidote.core import DependencyInstance, DependencyProvider


class DummyProvider(DependencyProvider):
    singleton = True

    def clone(self, keep_singletons_cache: bool) -> DependencyProvider:
        return DummyProvider(self.data)

    def __init__(self, data: Dict = None):
        super().__init__()
        self.frozen = False
        self.data = data

    def provide(self, dependency, container):
        try:
            return DependencyInstance(self.data[dependency],
                                      singleton=self.singleton)
        except KeyError:
            pass


class DummyFactoryProvider(DependencyProvider):
    singleton = True

    def clone(self, keep_singletons_cache: bool) -> DependencyProvider:
        return DummyFactoryProvider(self.data)

    def __init__(self, data: Dict = None):
        super().__init__()
        self.frozen = False
        self.data = data or dict()

    def provide(self, dependency, container):
        try:
            return DependencyInstance(self.data[dependency](container),
                                      singleton=self.singleton)
        except KeyError:
            pass
