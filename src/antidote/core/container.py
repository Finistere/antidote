import threading
from collections import deque
from contextlib import contextmanager
from typing import (Any, Callable, cast, Deque, Dict, Hashable, Iterator, List, Mapping,
                    Optional, Sequence, Tuple, Type)
from weakref import ref, ReferenceType

from .exceptions import (DependencyCycleError, DependencyInstantiationError,
                         DependencyNotFoundError, DuplicateDependencyError,
                         FrozenWorldError)
from .utils import DependencyDebug
from .._compatibility.typing import final
from .._internal import API
from .._internal.stack import DependencyStack
from .._internal.utils import FinalImmutable

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

    def __init__(self, value: Any, *, singleton: bool = False) -> None:
        super().__init__(value, singleton)

    def __eq__(self, other: object) -> bool:
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


###########
# PRIVATE #
###########

@API.private
class RawProvider:
    """
    Abstract base class for a Provider.

    Prefer using :py:class:`~.core.provider.Provider`
    or :py:class:`~.core.provider.StatelessProvider` which are safer
    to implement.

    :meta private:
    """

    def __init__(self) -> None:
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
    def _ensure_not_frozen(self) -> Iterator[None]:
        container_ref: 'ReferenceType[RawContainer]' = getattr(self,
                                                               _CONTAINER_REF_ATTR)
        if container_ref is None:
            yield
        else:
            container = container_ref()
            assert container is not None, "Associated container does not exist anymore."
            with container.ensure_not_frozen():
                yield

    @API.private
    @final
    def _raise_if_exists(self, dependency: Hashable) -> None:
        container_ref: 'ReferenceType[RawContainer]' = getattr(self,
                                                               _CONTAINER_REF_ATTR)
        if container_ref is not None:
            container = container_ref()
            assert container is not None, "Associated container does not exist anymore."
            container.raise_if_exists(dependency)
        else:
            if self.exists(dependency):
                raise DuplicateDependencyError(
                    f"{dependency} has already been registered in {type(self)}")

    @final
    @property
    def is_registered(self) -> bool:
        return getattr(self, _CONTAINER_REF_ATTR) is not None


@API.private  # Not meant for direct use. You should go through world to manipulate it.
class RawContainer(Container):

    def __init__(self) -> None:
        self._dependency_stack = DependencyStack()
        self._singleton_lock = threading.RLock()
        self._providers: List[RawProvider] = list()
        self._singletons: Dict[Any, Any] = dict()
        self.__freeze_lock = threading.RLock()
        self.__frozen = False

    def __repr__(self) -> str:
        return f"{type(self).__name__}(providers={', '.join(map(str, self._providers))})"

    @property
    def providers(self) -> Sequence[RawProvider]:
        return self._providers.copy()

    @contextmanager
    def ensure_not_frozen(self) -> Iterator[None]:
        with self.__freeze_lock:
            if self.__frozen:
                raise FrozenWorldError()
            yield

    def freeze(self) -> None:
        with self.__freeze_lock:
            self.__frozen = True

    def add_provider(self, provider_cls: Type[RawProvider]) -> None:
        if not isinstance(provider_cls, type) \
                or not issubclass(provider_cls, RawProvider):
            raise TypeError(
                f"provider must be a Provider, not a {provider_cls}")

        with self.ensure_not_frozen(), self._singleton_lock:
            if any(provider_cls == type(p) for p in self._providers):
                raise ValueError(f"Provider {provider_cls} already exists")

            provider = provider_cls()
            setattr(provider, _CONTAINER_REF_ATTR, ref(self))
            self._providers.append(provider)
            self._singletons[provider_cls] = provider

    def add_singletons(self, dependencies: Mapping[Hashable, object]) -> None:
        with self.ensure_not_frozen(), self._singleton_lock:
            for k, v in dependencies.items():
                self.raise_if_exists(k)
            self._singletons.update(dependencies)

    def raise_if_exists(self, dependency: Hashable) -> None:
        with self.__freeze_lock:
            if dependency in self._singletons:
                raise DuplicateDependencyError(
                    f"{dependency!r} has already been defined as a singleton pointing "
                    f"to {self._singletons[dependency]}")

            for provider in self._providers:
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
        container = type(self)()
        with self._singleton_lock:
            if keep_singletons:
                container._singletons = self._singletons.copy()
            if clone_providers:
                for p in self._providers:
                    clone = p.clone(keep_singletons_cache=keep_singletons)
                    if clone is p \
                        or getattr(clone, _CONTAINER_REF_ATTR,
                                   None) is not None:
                        raise RuntimeError(
                            "A Provider should always return a fresh "
                            "instance when copy() is called.")

                    setattr(clone, _CONTAINER_REF_ATTR, ref(container))
                    container._providers.append(clone)
                    container._singletons[type(p)] = clone
            else:
                for p in self._providers:
                    container.add_provider(type(p))

        return container

    def debug(self, dependency: Hashable) -> DependencyDebug:
        from .._internal.utils.debug import debug_repr

        with self.__freeze_lock:
            for p in self._providers:
                debug = p.maybe_debug(dependency)
                if debug is not None:
                    return debug
            try:
                value = self._singletons[dependency]
                return DependencyDebug(f"Singleton {debug_repr(dependency)} "
                                       f"-> {value!r}",
                                       singleton=True)
            except KeyError:
                raise DependencyNotFoundError(dependency)

    def provide(self, dependency: Hashable) -> DependencyInstance:
        try:
            return DependencyInstance(self._singletons[dependency], singleton=True)
        except KeyError:
            pass
        return self._safe_provide(dependency)

    def get(self, dependency: Hashable) -> Any:
        try:
            return self._singletons[dependency]
        except KeyError:
            pass
        return self._safe_provide(dependency).value

    def _safe_provide(self, dependency: Hashable) -> DependencyInstance:
        with self._singleton_lock:
            try:
                try:
                    return DependencyInstance(self._singletons[dependency],
                                              singleton=True)
                except KeyError:
                    pass

                with self._dependency_stack.instantiating(dependency):
                    for provider in self._providers:
                        dependency_instance = provider.maybe_provide(dependency, self)
                        if dependency_instance is not None:
                            if dependency_instance.singleton:
                                self._singletons[dependency] = dependency_instance.value

                            return dependency_instance

            except DependencyCycleError:
                raise

            except DependencyInstantiationError as e:
                if self._dependency_stack.depth == 0:
                    raise DependencyInstantiationError(dependency) from e
                else:
                    raise

            except Exception as e:
                raise DependencyInstantiationError(
                    dependency,
                    self._dependency_stack.to_list()) from e

            raise DependencyNotFoundError(dependency)


class OverridableRawContainer(RawContainer):
    def __init__(self) -> None:
        super().__init__()
        self.__override_lock = threading.RLock()
        # Used to differentiate singletons from the overrides and the "normal" ones.
        self.__singletons_override: Dict[Hashable, object] = dict()
        self.__factory_overrides: Dict[Hashable, Tuple[Callable[[], object], bool]] = {}
        self.__provider_overrides: Deque[
            Callable[[Any], Optional[DependencyInstance]]] = deque()

    @classmethod
    def build(cls,
              original: RawContainer,
              keep_singletons: bool) -> 'OverridableRawContainer':
        container = cls()
        clone = original.clone(keep_singletons=keep_singletons)
        container._singletons = clone._singletons
        container._providers = clone._providers
        if isinstance(clone, OverridableRawContainer):
            container.__singletons_override = clone.__singletons_override
            container.__factory_overrides = clone.__factory_overrides
            container.__provider_overrides = clone.__provider_overrides
        return container

    def override_singletons(self, singletons: Dict[Hashable, object]) -> None:
        if not isinstance(singletons, dict):
            raise TypeError(f"singletons must be a dict, not a {type(singletons)}")
        with self.__override_lock:
            self.__singletons_override.update(singletons)

    def override_factory(self,
                         dependency: Hashable,
                         *,
                         factory: Callable[[], Any],
                         singleton: bool) -> None:
        if not callable(factory):
            raise TypeError(f"factory must be a callable, not a {type(factory)}")
        if not isinstance(singleton, bool):
            raise TypeError(f"singleton must be a boolean, not a {type(singleton)}")
        with self.__override_lock:
            self.__factory_overrides[dependency] = (factory, singleton)

    def override_provider(self,
                          provider: Callable[[Any], Optional[DependencyInstance]]
                          ) -> None:
        if not callable(provider):
            raise TypeError(f"provider must be a callable, not a {type(provider)}")
        with self.__override_lock:
            self.__provider_overrides.appendleft(provider)  # latest provider wins

    def provide(self, dependency: Hashable) -> DependencyInstance:
        return self._safe_provide(dependency)

    def get(self, dependency: Hashable) -> object:
        return self._safe_provide(dependency).value

    def clone(self,
              *,
              keep_singletons: bool = False,
              clone_providers: bool = True) -> 'OverridableRawContainer':
        with self._singleton_lock, self.__override_lock:
            container = cast(OverridableRawContainer,
                             super().clone(keep_singletons=keep_singletons,
                                           clone_providers=clone_providers))
            if keep_singletons:
                container.__singletons_override = self.__singletons_override.copy()
            container.__factory_overrides = self.__factory_overrides.copy()
            container.__provider_overrides = self.__provider_overrides.copy()

        return container

    def debug(self, dependency: Hashable) -> DependencyDebug:
        from .._internal.utils.debug import debug_repr

        with self.__override_lock:
            try:
                value = self.__singletons_override[dependency]
            except KeyError:
                pass
            else:
                return DependencyDebug(f"Override/Singleton: {debug_repr(dependency)} "
                                       f"-> {value!r}",
                                       singleton=True)
            try:
                (factory, singleton) = self.__factory_overrides[dependency]
            except KeyError:
                pass
            else:
                return DependencyDebug(f"Override/Factory: {debug_repr(dependency)} "
                                       f"-> {debug_repr(factory)}",
                                       singleton=singleton)

        return super().debug(dependency)

    def _safe_provide(self, dependency: Hashable) -> DependencyInstance:
        with self._singleton_lock, self.__override_lock:
            with self._dependency_stack.instantiating(dependency):
                try:
                    return DependencyInstance(self.__singletons_override[dependency],
                                              singleton=True)
                except KeyError:
                    pass

                try:
                    for provider in self.__provider_overrides:
                        dependency_instance = provider(dependency)
                        if dependency_instance is not None:
                            if dependency_instance.singleton:
                                self.__singletons_override[dependency] \
                                    = dependency_instance.value
                            return dependency_instance

                    try:
                        (factory, singleton) = self.__factory_overrides[dependency]
                    except KeyError:
                        pass
                    else:
                        value = factory()
                        if singleton:
                            self.__singletons_override[dependency] = value
                        return DependencyInstance(value, singleton=singleton)

                except DependencyCycleError:
                    raise

                except Exception as e:
                    raise DependencyInstantiationError(dependency) from e

            return super()._safe_provide(dependency)
