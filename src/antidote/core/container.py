import threading
from typing import (Any, Dict, final, Generic, Hashable, List, Mapping, Optional, TypeVar)

from .exceptions import (DependencyCycleError, DependencyInstantiationError,
                         DependencyNotFoundError, FrozenWorldError)
from .._internal.stack import DependencyStack
from .._internal.utils import API, FinalMeta, SlotsReprMixin

T = TypeVar('T')


@final
@API.public
class DependencyInstance(SlotsReprMixin, Generic[T], metaclass=FinalMeta):
    """
    Simple wrapper used by a :py:class:`~.core.Provider` when returning an
    instance of a dependency so it can specify in which scope the instance
    belongs to.
    """
    __slots__ = ('instance', 'singleton')

    def __init__(self, instance: T, singleton: bool = False):
        self.instance = instance
        self.singleton = singleton


@final
@API.public
class DependencyContainer(metaclass=FinalMeta):
    """
    Instantiates the dependencies through the registered providers and handles
    their scope.
    """

    def __init__(self):
        self.__providers: List[DependencyProvider] = list()
        self.__singletons: Dict[Any, Any] = dict()
        self.__singletons[DependencyContainer] = self
        self.__dependency_stack = DependencyStack()
        self.__instantiation_lock = threading.RLock()
        self.__frozen = False

    def __str__(self):
        return f"{type(self).__name__}(providers={', '.join(map(str, self.__providers))})"

    def __repr__(self):
        return f"{type(self).__name__}(providers={', '.join(map(repr, self.__providers))})"

    @API.private  # Use world.freeze() instead
    def freeze(self):
        with self.__instantiation_lock:
            self.__frozen = True
            for provider in self.__providers:
                provider.freeze()

    @API.private  # Not to be used directly, only used by world to create test worlds
    def clone(self, keep_singletons: bool = False) -> 'DependencyContainer':
        c = DependencyContainer()
        with self.__instantiation_lock:
            c.__singletons = self.__singletons.copy() if keep_singletons else dict()
            c.__providers = [p.clone() for p in self.__providers]
            c.__singletons[DependencyContainer] = c
            for p in c.__providers:
                c.__singletons[type(p)] = p
        return c

    @API.private  # Use the @provider decorator
    def register_provider(self, provider: 'DependencyProvider'):
        if not isinstance(provider, DependencyProvider):
            raise TypeError(
                f"provider must be a DependencyProvider, not a {type(provider)!r}")

        with self.__instantiation_lock:
            if self.__frozen:
                raise FrozenWorldError(f"Cannot add provider {type(provider)} "
                                       f"to a frozen container.")
            self.__providers.append(provider)
            self.__singletons[type(provider)] = provider

    @API.private  # Use world instead
    def update_singletons(self, dependencies: Mapping):
        with self.__instantiation_lock:
            if self.__frozen:
                raise FrozenWorldError(f"Cannot add singletons to a frozen container. "
                                       f"singletons = {dependencies}")
            self.__singletons.update(dependencies)

    @API.public
    def get(self, dependency: Hashable) -> Any:
        try:
            return self.__singletons[dependency]
        except KeyError:
            pass
        return self.__safe_provide(dependency).instance

    @API.public
    def provide(self, dependency: Hashable) -> DependencyInstance:
        try:
            return DependencyInstance(self.__singletons[dependency], singleton=True)
        except KeyError:
            pass
        return self.__safe_provide(dependency)

    def __safe_provide(self, dependency: Hashable) -> Optional[DependencyInstance]:
        try:
            with self.__instantiation_lock, \
                 self.__dependency_stack.instantiating(dependency):
                try:
                    return DependencyInstance(self.__singletons[dependency],
                                              singleton=True)
                except KeyError:
                    pass

                for provider in self.__providers:
                    dependency_instance = provider.provide(dependency, self)
                    if dependency_instance is not None:
                        if dependency_instance.singleton:
                            self.__singletons[dependency] = dependency_instance.instance

                        return dependency_instance

        except DependencyCycleError:
            raise

        except Exception as e:
            raise DependencyInstantiationError(dependency) from e

        else:
            raise DependencyNotFoundError(dependency)


@API.public
class DependencyProvider:
    """
    Abstract base class for a Provider.

    Used by the :py:class:`~.core.DependencyContainer` to instantiate
    dependencies. Several are used in a cooperative manner : the first instance
    to be returned by one of them is used. Thus providers should ideally not
    overlap and handle only one kind of dependencies such as strings or tag.

    This should be used whenever one needs to introduce a new kind of dependency,
    or control how certain dependencies are instantiated.
    """

    @API.private  # Should be used through world.freeze()
    def freeze(self):
        raise NotImplementedError()  # pragma: no cover

    @API.public_for_tests
    def world_provide(self, dependency: Hashable):
        """
        Method only used for tests to avoid the repeated injection of the current
        DependencyContainer.
        """
        from antidote import world
        return self.provide(dependency, world.get(DependencyContainer))

    # Use world_provide for tests and you should go through world to get what you need
    @API.private
    def provide(self, dependency: Hashable, container: DependencyContainer
                ) -> Optional[DependencyInstance]:
        """
        Method called by the :py:class:`~.core.DependencyContainer` when
        searching for a dependency.

        It is necessary to check quickly if the dependency can be provided or
        not, as :py:class:`~.core.DependencyContainer` will try its
        registered providers. A good practice is to subclass
        :py:class:`~.core.Dependency` so custom dependencies be differentiated.

        Args:
            dependency: The dependency to be provided by the provider.
            container: current container

        Returns:
            The requested instance wrapped in a :py:class:`~.core.Instance`
            if available or :py:obj:`None`.
        """
        raise NotImplementedError()  # pragma: no cover

    @API.private  # Only used for world.test.clone()
    def clone(self) -> 'DependencyProvider':
        raise NotImplementedError()  # pragma: no cover
