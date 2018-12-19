import threading
from abc import ABC, abstractmethod
from typing import List, Optional

from .stack import InstantiationStack
from .._internal.utils import SlotReprMixin
from ..exceptions import (DependencyCycleError, DependencyInstantiationError,
                          DependencyNotFoundError)


class DependencyContainer:
    SENTINEL = object()

    def __init__(self):
        self._providers = list()  # type: List[Provider]
        self._singletons = dict()
        self._instantiation_lock = threading.RLock()
        self._instantiation_stack = InstantiationStack()

    @property
    def providers(self):
        return {type(p): p for p in self._providers}

    @property
    def singletons(self):
        return self._singletons.copy()

    def register_provider(self, provider):
        if not isinstance(provider, Provider):
            raise ValueError("Not a provider")

        self._providers.append(provider)

    def __str__(self):
        return "{}(providers=({}))".format(
            type(self).__name__,
            ", ".join("{}={}".format(name, p)
                      for name, p in self.providers.items()),
        )

    def __repr__(self):
        return "{}(providers=({}), singletons={!r})".format(
            type(self).__name__,
            ", ".join("{!r}={!r}".format(name, p)
                      for name, p in self.providers.items()),
            self._singletons
        )

    def __setitem__(self, dependency_id, dependency):
        """
        Set a dependency in the cache.
        """
        with self._instantiation_lock:
            self._singletons[dependency_id] = dependency

    def __delitem__(self, dependency_id):
        """
        Delete a dependency in the cache.
        """
        with self._instantiation_lock:
            del self._singletons[dependency_id]

    def update(self, *args, **kwargs):
        """
        Update the cached dependencies.
        """
        with self._instantiation_lock:
            self._singletons.update(*args, **kwargs)

    def __getitem__(self, dependency_id):
        instance = self.provide(dependency_id)
        if instance is self.SENTINEL:
            raise DependencyNotFoundError(dependency_id)
        return instance

    def provide(self, dependency):
        try:
            return self._singletons[dependency]
        except KeyError:
            pass

        try:
            with self._instantiation_lock, \
                    self._instantiation_stack.instantiating(dependency):
                try:
                    return self._singletons[dependency]
                except KeyError:
                    pass

                for provider in self._providers:
                    instance = provider.provide(
                        dependency
                        if isinstance(dependency, Dependency) else
                        Dependency(dependency)
                    )
                    if instance is not None:
                        if instance.singleton:
                            self._singletons[dependency] = instance.item

                        return instance.item

        except DependencyCycleError:
            raise

        except Exception as e:
            raise DependencyInstantiationError(dependency) from e

        return self.SENTINEL


class Dependency(SlotReprMixin):
    __slots__ = ('id',)

    def __init__(self, id):
        assert id is not None
        assert not isinstance(id, Dependency)
        self.id = id

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return (self.id == other
                or (isinstance(other, Dependency) and self.id == other.id))


class Instance(SlotReprMixin):
    """
    Simple wrapper which has to be used by providers when returning an
    instance of a dependency.

    This enables the container to know if the returned dependency needs to
    be cached or not (singleton).
    """
    __slots__ = ('item', 'singleton')

    def __init__(self, item, singleton: bool = False):  # pragma: no cover
        self.item = item
        self.singleton = singleton


class Provider(ABC):
    @abstractmethod
    def provide(self, dependency: Dependency) -> Optional[Instance]:
        """
        Method called by the :py:class:`~.container.DependencyContainer` when
        searching for a dependency.

        All providers all called sequentially until one returns an
        :py:class:`~.container.Instance`. Thus it is necessary to check quickly
        if the dependency cannot be provided. A good practice is to subclass
        :py:class:`~.container.Dependency` so they can be differentiated.

        Args:
            dependency: The dependency to be provided by the provider.

        Returns:
            The requested instance wrapped in a :py:class:`~.container.Instance`
            if available or :py:obj:`None`.
        """
