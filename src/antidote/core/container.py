import threading
from typing import (Any, cast, Dict, Generic, Hashable, List, Mapping, Optional, Tuple,
                    TypeVar)

from .exceptions import (DependencyCycleError, DependencyInstantiationError,
                         DependencyNotFoundError)
from .._internal.stack import DependencyStack
from .._internal.utils import SlotsReprMixin

T = TypeVar('T')


class DependencyInstance(SlotsReprMixin, Generic[T]):
    """
    Simple wrapper used by a :py:class:`~.core.Provider` when returning an
    instance of a dependency so it can specify in which scope the instance
    belongs to.
    """
    __slots__ = ('instance', 'singleton')

    def __init__(self, instance: T, singleton: bool = False):
        self.instance = instance
        self.singleton = singleton


class DependencyContainer:
    """
    Instantiates the dependencies through the registered providers and handles
    their scope.
    """

    def __init__(self):
        self._providers = list()  # type: List[DependencyProvider]
        self._type_to_provider = dict()  # type: Dict[type, DependencyProvider]
        self._singletons = dict()  # type: Dict[Any, DependencyInstance]
        self._singletons[DependencyContainer] = DependencyInstance(self, singleton=True)
        self._dependency_stack = DependencyStack()
        self._instantiation_lock = threading.RLock()

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

    @property
    def providers(self) -> Mapping[type, 'DependencyProvider']:
        """ Returns a mapping of all the registered providers by their type. """
        return {type(p): p for p in self._providers}

    @property
    def singletons(self) -> dict:
        """ Returns all the defined singletons """
        return self._singletons.copy()

    def register_provider(self, provider: 'DependencyProvider'):
        """
        Registers a provider, which can then be used to instantiate dependencies.

        Args:
            provider: Provider instance to be registered.

        """
        if not isinstance(provider, DependencyProvider):
            raise TypeError("provider must be a DependencyProvider, not a {!r}".format(
                type(provider)
            ))

        for bound_type in provider.bound_dependency_types:
            if bound_type in self._type_to_provider:
                raise RuntimeError(
                    "Cannot bind {!r} to provider, already bound to {!r}".format(
                        bound_type, self._type_to_provider[bound_type]
                    ))

        for bound_type in provider.bound_dependency_types:
            self._type_to_provider[bound_type] = provider

        self._providers.append(provider)

    def update_singletons(self, dependencies: Mapping):
        """
        Update the singletons.
        """
        with self._instantiation_lock:
            self._singletons.update({
                k: DependencyInstance(v, singleton=True)
                for k, v in dependencies.items()
            })

    def get(self, dependency: Hashable):
        """
        Returns an instance for the given dependency. All registered providers
        are called sequentially until one returns an instance.  If none is
        found, :py:exc:`~.exceptions.DependencyNotFoundError` is raised.

        Args:
            dependency: Passed on to the registered providers.

        Returns:
            instance for the given dependency
        """
        return self.safe_provide(dependency).instance

    def safe_provide(self, dependency: Hashable) -> DependencyInstance:
        dependency_instance = self.provide(dependency)
        if dependency_instance is None:
            raise DependencyNotFoundError(dependency)
        return dependency_instance

    def provide(self, dependency: Hashable) -> Optional[DependencyInstance]:
        """
        Internal method which should not be directly called. Prefer
        :py:meth:`~.core.core.DependencyContainer.get`.
        It may be overridden in a subclass to customize how dependencies are
        instantiated.

        Used by the injection wrappers.
        """
        try:
            return self._singletons[dependency]
        except KeyError:
            pass

        try:
            # @formatter:off
            with self._instantiation_lock, \
                    self._dependency_stack.instantiating(dependency):
                # @formatter:on
                try:
                    return self._singletons[dependency]
                except KeyError:
                    pass

                dependency_instance = None
                provider = self._type_to_provider.get(type(dependency))
                if provider is not None:
                    dependency_instance = provider.provide(dependency)
                else:
                    for provider in self._providers:
                        dependency_instance = provider.provide(dependency)
                        if dependency_instance is not None:
                            break

                if dependency_instance is not None:
                    if dependency_instance.singleton:
                        self._singletons[dependency] = dependency_instance

                    return dependency_instance

        except DependencyCycleError:
            raise

        except Exception as e:
            raise DependencyInstantiationError(dependency) from e

        return None


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
    bound_dependency_types = cast(Tuple[type], ())  # type: Tuple[type, ...]

    def __init__(self, container: DependencyContainer):
        self._container = container  # type: DependencyContainer

    def provide(self, dependency: Hashable) -> Optional[DependencyInstance]:
        """
        Method called by the :py:class:`~.core.DependencyContainer` when
        searching for a dependency.

        It is necessary to check quickly if the dependency can be provided or
        not, as :py:class:`~.core.DependencyContainer` will try its
        registered providers. A good practice is to subclass
        :py:class:`~.core.Dependency` so custom dependencies be differentiated.

        Args:
            dependency: The dependency to be provided by the provider.

        Returns:
            The requested instance wrapped in a :py:class:`~.core.Instance`
            if available or :py:obj:`None`.
        """
        raise NotImplementedError()  # pragma: no cover
