import threading
from collections import deque
from contextlib import contextmanager
from typing import (Callable, cast, Deque, Dict, Hashable, Iterator, List,
                    Mapping, Optional, Sequence, Tuple, Type, TYPE_CHECKING)
from weakref import ref, ReferenceType

from .exceptions import (DependencyCycleError, DependencyInstantiationError,
                         DependencyNotFoundError, DuplicateDependencyError,
                         FrozenWorldError)

from .._compatibility.typing import final
from .._internal import API
from .._internal.stack import DependencyStack
from .._internal.utils import FinalImmutable

if TYPE_CHECKING:
    from .utils import DependencyDebug

# PRIVATE
_CONTAINER_REF_ATTR = "_antidote__container_ref"


@API.public
@final
class Scope(FinalImmutable):
    __slots__ = ('name',)
    name: str

    def __repr__(self) -> str:
        return f"Scope(name='{self.name}')"

    @staticmethod
    @API.public
    def singleton() -> 'Scope':
        return _SCOPE_SINGLETON

    @staticmethod
    @API.public
    def sentinel() -> 'Scope':
        return _SCOPE_SENTINEL


# Use Scope.singleton() instead.
# API.private
_SCOPE_SINGLETON = Scope('singleton')
_SCOPE_SENTINEL = Scope('__sentinel__')


@API.public
@final
class DependencyInstance(FinalImmutable):
    """
    Simple wrapper of a dependency instance given by a
    :py:class:`~.provider.Provider`.
    """
    __slots__ = ('value', 'scope')
    value: object
    scope: Scope

    def __init__(self,
                 value: object,
                 *,
                 scope: Optional[Scope] = None) -> None:
        assert scope is not _SCOPE_SENTINEL
        super().__init__(value=value, scope=scope)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, DependencyInstance) \
               and self.value == other.value \
               and self.scope is other.scope  # noqa: E126

    def is_singleton(self) -> bool:
        return self.scope is _SCOPE_SINGLETON


@API.public
class Container:
    """
    Public interface of the container used by Antidote to handles all
    dependencies. Used in a :py:class:`~.provider.Provider` to access other
    dependencies.
    """

    def get(self, dependency: Hashable) -> object:
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

    def maybe_debug(self, dependency: Hashable) -> 'Optional[DependencyDebug]':
        raise NotImplementedError()  # pragma: no cover

    @API.private
    @final
    @contextmanager
    def _bound_container_ensure_not_frozen(self) -> Iterator[None]:
        container = self.__bound_container()
        if container is not None:
            with container.ensure_not_frozen():
                yield
        else:
            yield

    @API.private
    @final
    @contextmanager
    def _bound_container_locked(self) -> Iterator[None]:
        container = self.__bound_container()
        if container is not None:
            with container.locked():
                yield
        else:
            yield

    @API.private
    @final
    def _bound_container_raise_if_exists(self, dependency: Hashable) -> None:
        container = self.__bound_container()
        if container is not None:
            container.raise_if_exists(dependency)
        else:
            if self.exists(dependency):
                raise DuplicateDependencyError(
                    f"{dependency} has already been registered in {type(self)}")

    @API.private
    def __bound_container(self) -> 'Optional[RawContainer]':
        container_ref: 'ReferenceType[RawContainer]' = getattr(self,
                                                               _CONTAINER_REF_ATTR)
        if container_ref is not None:
            container = container_ref()
            assert container is not None, "Associated container does not exist anymore."
            return container
        return None

    # API.private
    @final
    @property
    def is_registered(self) -> bool:
        return getattr(self, _CONTAINER_REF_ATTR) is not None


@API.private  # Not meant for direct use. You should go through world to manipulate it.
class RawContainer(Container):

    def __init__(self) -> None:
        self._dependency_stack = DependencyStack()
        self._instantiation_lock = threading.RLock()
        self._providers: List[RawProvider] = list()
        self._singletons: Dict[object, object] = dict()
        self._scopes: Dict[Scope, Dict[object, object]] = dict()
        self._is_clone: bool = False
        self._freeze_lock = threading.RLock()
        self.__frozen = False

    def __repr__(self) -> str:
        return f"{type(self).__name__}(providers={', '.join(map(str, self._providers))})"

    @property
    def is_clone(self) -> bool:
        return self._is_clone

    def create_scope(self, name: str) -> Scope:
        assert all(s.name != name for s in self._scopes.keys())
        assert len(self._scopes) < 255
        s = Scope(name)  # Name is only a helper, not a identifier by itself.
        self._scopes[s] = dict()
        return s

    def reset_scope(self, scope: Scope) -> None:
        self._scopes[scope] = dict()

    @property
    def scopes(self) -> Sequence[Scope]:
        return list(self._scopes.keys())

    @property
    def providers(self) -> Sequence[RawProvider]:
        return self._providers.copy()

    @contextmanager
    def locked(self) -> Iterator[None]:
        with self._freeze_lock, self._instantiation_lock:
            yield

    @contextmanager
    def ensure_not_frozen(self) -> Iterator[None]:
        with self._freeze_lock:
            if self.__frozen:
                raise FrozenWorldError()
            yield

    def freeze(self) -> None:
        with self._freeze_lock:
            self.__frozen = True

    def add_provider(self, provider_cls: Type[RawProvider]) -> None:
        with self.ensure_not_frozen(), self._instantiation_lock:
            assert all(provider_cls != type(p) for p in self._providers)
            provider = provider_cls()
            setattr(provider, _CONTAINER_REF_ATTR, ref(self))
            self._providers.append(provider)
            self._singletons[provider_cls] = provider

    def add_singletons(self, dependencies: Mapping[Hashable, object]) -> None:
        with self.ensure_not_frozen(), self._instantiation_lock:
            for k, v in dependencies.items():
                self.raise_if_exists(k)
            self._singletons.update(dependencies)

    def raise_if_exists(self, dependency: Hashable) -> None:
        with self._freeze_lock:
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
              keep_singletons: bool,
              keep_scopes: bool) -> 'RawContainer':
        container: RawContainer = type(self)()
        container._is_clone = True
        with self.locked():
            if keep_singletons:
                container._singletons = self._singletons.copy()

            container._scopes = {
                scope: dependencies.copy() if keep_scopes else dict()
                for scope, dependencies in self._scopes.items()
            }

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

        return container

    def debug(self, dependency: Hashable) -> 'DependencyDebug':
        from .._internal.utils.debug import debug_repr
        from .utils import DependencyDebug

        with self.locked():
            for p in self._providers:
                debug = p.maybe_debug(dependency)
                if debug is not None:
                    return debug
            try:
                value = self._singletons[dependency]
                return DependencyDebug(f"Singleton: {debug_repr(dependency)} "
                                       f"-> {value!r}",
                                       scope=Scope.singleton())
            except KeyError:
                raise DependencyNotFoundError(dependency)

    def provide(self, dependency: Hashable) -> DependencyInstance:
        try:
            return DependencyInstance(self._singletons[dependency],
                                      scope=Scope.singleton())
        except KeyError:
            pass
        return self._safe_provide(dependency)

    def get(self, dependency: Hashable) -> object:
        try:
            return self._singletons[dependency]
        except KeyError:
            pass
        return self._safe_provide(dependency).value

    def _safe_provide(self, dependency: Hashable) -> DependencyInstance:
        with self._instantiation_lock:
            try:
                try:
                    return DependencyInstance(self._singletons[dependency],
                                              scope=Scope.singleton())
                except KeyError:
                    pass

                for scope, dependencies in self._scopes.items():
                    try:
                        return DependencyInstance(dependencies[dependency],
                                                  scope=scope)
                    except KeyError:
                        pass

                with self._dependency_stack.instantiating(dependency):
                    for provider in self._providers:
                        di = provider.maybe_provide(dependency, self)
                        if di is not None:
                            if di.is_singleton():
                                self._singletons[dependency] = di.value
                            elif di.scope is not None:
                                self._scopes[di.scope][dependency] = di.value

                            return di

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
        from collections import defaultdict
        super().__init__()
        self._is_clone = True
        self.__override_lock = threading.RLock()
        # Used to differentiate singletons from the overrides and the "normal" ones.
        self.__singletons_override: Dict[Hashable, object] = dict()
        self.__scopes_override: Dict[Scope, Dict[Hashable, object]] = defaultdict(dict)
        self.__factory_overrides: Dict[
            Hashable, Tuple[Callable[[], object], Optional[Scope]]] = {}
        self.__provider_overrides: Deque[
            Callable[[Hashable], Optional[DependencyInstance]]] = deque()

    @classmethod
    def from_clone(cls, cloned: RawContainer) -> 'OverridableRawContainer':
        container = cls()
        container._singletons = cloned._singletons
        container._scopes = cloned._scopes
        container._providers = cloned._providers
        if isinstance(cloned, OverridableRawContainer):
            container.__singletons_override = cloned.__singletons_override
            container.__factory_overrides = cloned.__factory_overrides
            container.__provider_overrides = cloned.__provider_overrides
        return container

    def override_singletons(self, singletons: Dict[Hashable, object]) -> None:
        with self.__override_lock:
            self.__singletons_override.update(singletons)

    def override_factory(self,
                         dependency: Hashable,
                         *,
                         factory: Callable[[], object],
                         scope: Optional[Scope]) -> None:
        with self.__override_lock:
            self.__factory_overrides[dependency] = (factory, scope)

    def override_provider(self,
                          provider: Callable[[Hashable], Optional[DependencyInstance]]
                          ) -> None:
        with self.__override_lock:
            self.__provider_overrides.appendleft(provider)  # latest provider wins

    def reset_scope(self, scope: Scope) -> None:
        super().reset_scope(scope)
        self.__scopes_override[scope] = dict()

    def provide(self, dependency: Hashable) -> DependencyInstance:
        return self._safe_provide(dependency)

    def get(self, dependency: Hashable) -> object:
        return self._safe_provide(dependency).value

    def clone(self,
              *,
              keep_singletons: bool,
              keep_scopes: bool) -> 'OverridableRawContainer':
        with self.__override_lock:
            container = cast(OverridableRawContainer,
                             super().clone(keep_singletons=keep_singletons,
                                           keep_scopes=keep_scopes))
            if keep_singletons:
                container.__singletons_override = self.__singletons_override.copy()
            container.__scopes_override = {
                scope: dependencies.copy() if keep_scopes else dict()
                for scope, dependencies in self.__scopes_override.items()
            }
            container.__factory_overrides = self.__factory_overrides.copy()
            container.__provider_overrides = self.__provider_overrides.copy()

        return container

    def debug(self, dependency: Hashable) -> 'DependencyDebug':
        from .._internal.utils.debug import debug_repr
        from .utils import DependencyDebug

        with self.__override_lock:
            try:
                value = self.__singletons_override[dependency]
            except KeyError:
                pass
            else:
                return DependencyDebug(f"Override/Singleton: {debug_repr(dependency)} "
                                       f"-> {value!r}",
                                       scope=Scope.singleton())
            try:
                (factory, scope) = self.__factory_overrides[dependency]
            except KeyError:
                pass
            else:
                return DependencyDebug(f"Override/Factory: {debug_repr(dependency)} "
                                       f"-> {debug_repr(factory)}",
                                       scope=scope)

        return super().debug(dependency)

    def _safe_provide(self, dependency: Hashable) -> DependencyInstance:
        with self._instantiation_lock, self.__override_lock:
            with self._dependency_stack.instantiating(dependency):
                try:
                    return DependencyInstance(self.__singletons_override[dependency],
                                              scope=Scope.singleton())
                except KeyError:
                    pass

                for scope_, dependencies in self.__scopes_override.items():
                    try:
                        return DependencyInstance(dependencies[dependency], scope=scope_)
                    except KeyError:
                        pass

                try:
                    for provider in self.__provider_overrides:
                        di = provider(dependency)
                        if di is not None:
                            if di.scope is Scope.singleton():
                                self.__singletons_override[dependency] = di.value
                            elif di.scope is not None:
                                self.__scopes_override[di.scope][dependency] = di.value
                            return di

                    try:
                        (factory, scope) = self.__factory_overrides[dependency]
                    except KeyError:
                        pass
                    else:
                        value = factory()
                        if scope is Scope.singleton():
                            self.__singletons_override[dependency] = value
                        elif scope is not None:
                            self.__scopes_override[scope_][dependency] = value
                        return DependencyInstance(value, scope=scope)

                except DependencyCycleError:
                    raise

                except Exception as e:
                    raise DependencyInstantiationError(dependency) from e

            return super()._safe_provide(dependency)
