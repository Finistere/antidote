from abc import ABC, abstractmethod

from ..container import Dependency, Instance


class Provider(ABC):
    @abstractmethod
    def __antidote_provide__(self, dependency: Dependency) -> Instance:
        """ Instantiate the dependency or raises DependencyNotProvidableError """
