import threading
from contextlib import contextmanager
from typing import Any, Dict, Hashable, List, Mapping, Optional, Sequence, Type
from weakref import ref, ReferenceType

from .exceptions import (DependencyCycleError, DependencyInstantiationError,
                         DependencyNotFoundError, DuplicateDependencyError,
                         FrozenContainerError)
from .utils import DependencyDebug
from .._compatibility.typing import final
from .._internal import API
from .._internal.stack import DependencyStack
from .._internal.utils import FinalImmutable, FinalMeta

# PRIVATE
_CONTAINER_REF_ATTR = "_antidote__container_ref"


@API.public
@final
class DependencyInstance(FinalImmutable):
    """
    Simple wrapper of a dependency instance given by a
    :py:class:`~.provider.Provider`.
    """
    __slots__ = ('value', 'singleton')
    value: Any
    singleton: bool

    def __init__(self, value: Any, singleton: bool = False):
        super().__init__(value, singleton)

    def __eq__(self, other):
        return isinstance(other, DependencyInstance) \
               and self.singleton == other.singleton \
               and self.value == other.value  # noqa: E126


@API.public
class Container:
    """
    Public interface of the container used by Antidote to handles all
    dependencies. Used in a :py:class:`~.provider.Provider` to access other
    dependencies.
    """

    def get(self, dependency: Hashable) -> Any:
        """
        Retrieves given dependency or raises a
        :py:exc:`~..exceptions.DependencyNotFoundError`.

        Args:
            dependency: Dependency to be retrieved.

        Returns:
            The dependency instance.
        """
        raise NotImplementedError()  # pragma: no cover

    def provide(self, dependency: Hashable) -> DependencyInstance:
        """
        Similar to :py:meth:`~.get` it will retrieve a dependency. However it will
        be wrapped in a :py:class:`~.DependencyInstance` if found. If not
        :py:obj:`None` will be returned. This allows to get additional information such
        as whether the dependency is a singleton or not.

        Args:
            dependency: Dependency to be retrieved.

        Returns:
            wrapped dependency instance.

        """
        raise NotImplementedError()  # pragma: no cover


@API.private
class RawProvider:
    """
    Abstract base class for a Provider.

    Prefer using :py:class:`~.core.provider.Provider`
    or :py:class:`~.core.provider.StatelessProvider` which are safer
    to implement.

    :meta private:
    """

    def __init__(self):
        setattr(self, _CONTAINER_REF_ATTR, None)

    def clone(self, keep_singletons_cache: bool) -> 'RawProvider':
        raise NotImplementedError()  # pragma: no cover

    def exists(self, dependency: Hashable) -> bool:
        raise NotImplementedError()  # pragma: no cover

    def maybe_provide(self, dependency: Hashable, container: Container
                      ) -> Optional[DependencyInstance]:
        raise NotImplementedError()  # pragma: no cover

    def maybe_debug(self, dependency: Hashable) -> Optional[DependencyDebug]:
        raise NotImplementedError()  # pragma: no cover

    @API.private
    @final
    @contextmanager
    def _ensure_not_frozen(self):
        container_ref: ReferenceType[Container] = getattr(self,
                                                          _CONTAINER_REF_ATTR)
        if container_ref is None:
            yield
        else:
            container: RawContainer = container_ref()
            assert container is not None, "Associated container does not exist anymore."
            with container.ensure_not_frozen():
                yield

    @API.private
    @final
    def _raise_if_exists(self, dependency):
        container_ref: ReferenceType[Container] = getattr(self,
                                                          _CONTAINER_REF_ATTR)
        if container_ref is not None:
            container: RawContainer = container_ref()
            assert container is not None, "Associated container does not exist anymore."
            container.raise_if_exists(dependency)
        else:
            if self.exists(dependency):
                raise DuplicateDependencyError(
                    f"{dependency} has already been registered in {type(self)}")

    @final
    @property
    def is_registered(self):
        return getattr(self, _CONTAINER_REF_ATTR) is not None


@final
@API.private  # Not meant for direct use. You should go through world to manipulate it.
class RawContainer(Container, metaclass=FinalMeta):
    """
    Reference implementation for the Container. The Cython version is
    considerably more complex for better performance.

    :meta private:
    """

    def __init__(self):
        self.__providers: List[RawProvider] = list()
        self.__singletons: Dict[Any, Any] = dict()
        self.__dependency_stack = DependencyStack()
        self.__singleton_lock = threading.RLock()
        self.__freeze_lock = threading.RLock()
        self.__frozen = False

    def __repr__(self):
        return f"{type(self).__name__}(providers={', '.join(map(str, self.__providers))})"

    @property
    def providers(self) -> Sequence[RawProvider]:
        return self.__providers.copy()

    @contextmanager
    def ensure_not_frozen(self):
        with self.__freeze_lock:
            if self.__frozen:
                raise FrozenContainerError()
            yield

    def freeze(self):
        with self.__freeze_lock:
            self.__frozen = True

    def add_provider(self, provider_cls: Type[RawProvider]):
        if not isinstance(provider_cls, type) \
                or not issubclass(provider_cls, RawProvider):
            raise TypeError(
                f"provider must be a Provider, not a {provider_cls}")

        with self.ensure_not_frozen(), self.__singleton_lock:
            if any(provider_cls == type(p) for p in self.__providers):
                raise ValueError(f"Provider {provider_cls} already exists")

            provider = provider_cls()
            setattr(provider, _CONTAINER_REF_ATTR, ref(self))
            self.__providers.append(provider)
            self.__singletons[provider_cls] = provider

    def add_singletons(self, dependencies: Mapping):
        with self.ensure_not_frozen(), self.__singleton_lock:
            for k, v in dependencies.items():
                self.raise_if_exists(k)
            self.__singletons.update(dependencies)

    def raise_if_exists(self, dependency: Hashable):
        with self.__freeze_lock:
            if dependency in self.__singletons:
                raise DuplicateDependencyError(
                    f"{dependency!r} has already been defined as a singleton pointing "
                    f"to {self.__singletons[dependency]}")

            for provider in self.__providers:
                if provider.exists(dependency):
                    debug = provider.maybe_debug(dependency)
                    message = f"{dependency!r} has already been declared " \
                              f"in {type(provider)}"
                    if debug is None:
                        raise DuplicateDependencyError(message)
                    else:
                        raise DuplicateDependencyError(message + f"\n{debug.info}")

    def clone(self,
              *,
              keep_singletons: bool = False,
              clone_providers: bool = True) -> 'RawContainer':
        c = RawContainer()
        with self.__singleton_lock:
            if keep_singletons:
                c.__singletons = self.__singletons.copy()
            if clone_providers:
                for p in self.__providers:
                    clone = p.clone(keep_singletons_cache=keep_singletons)
                    if clone is p \
                            or getattr(clone, _CONTAINER_REF_ATTR,
                                       None) is not None:
                        raise RuntimeError(
                            "A Provider should always return a fresh "
                            "instance when copy() is called.")

                    setattr(clone, _CONTAINER_REF_ATTR, ref(c))
                    c.__providers.append(clone)
                    c.__singletons[type(p)] = clone
            else:
                for p in self.__providers:
                    c.add_provider(type(p))

        return c

    def provide(self, dependency: Hashable) -> DependencyInstance:
        try:
            return DependencyInstance(self.__singletons[dependency], singleton=True)
        except KeyError:
            pass
        return self.__safe_provide(dependency)

    def get(self, dependency: Hashable) -> Any:
        try:
            return self.__singletons[dependency]
        except KeyError:
            pass
        return self.__safe_provide(dependency).value

    def __safe_provide(self, dependency: Hashable) -> DependencyInstance:
        try:
            with self.__singleton_lock, \
                 self.__dependency_stack.instantiating(dependency):
                try:
                    return DependencyInstance(self.__singletons[dependency],
                                              singleton=True)
                except KeyError:
                    pass

                for provider in self.__providers:
                    dependency_instance = provider.maybe_provide(dependency, self)
                    if dependency_instance is not None:
                        if dependency_instance.singleton:
                            self.__singletons[dependency] = dependency_instance.value

                        return dependency_instance

        except DependencyCycleError:
            raise

        except Exception as e:
            raise DependencyInstantiationError(dependency) from e

        raise DependencyNotFoundError(dependency)
