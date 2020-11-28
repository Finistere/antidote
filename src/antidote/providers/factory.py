import weakref
from typing import Any, Callable, Dict, Hashable, Optional, Union

from .service import Build
from .._internal import API
from .._internal.utils import debug_repr, FinalImmutable, SlotRecord
from ..core import Container, Dependency, DependencyInstance, Provider
from ..core.utils import DependencyDebug


@API.private
class FactoryProvider(Provider):
    def __init__(self):
        super().__init__()
        self.__factories: Dict[Hashable, Factory] = dict()

    def __repr__(self):
        return f"{type(self).__name__}(factories={self.__factories})"

    def clone(self, keep_singletons_cache: bool) -> 'FactoryProvider':
        p = FactoryProvider()
        if keep_singletons_cache:
            factories = {
                k: (f.copy() if f.dependency is not None else f)
                for k, f in self.__factories.items()
            }
        else:
            factories = {
                k: (f.copy(function=None) if f.dependency is not None else f)
                for k, f in self.__factories.items()
            }
        p.__factories = factories
        return p

    def exists(self, dependency: Hashable) -> bool:
        # For now we don't support multiple factories for a single dependency. Neither
        # is sharing the dependency with another provider. Simply because I don't see a
        # use case where it would make sense.
        # Open for discussions though, create an issue if you a use case.
        if isinstance(dependency, Build):
            dependency = dependency.dependency
        return (isinstance(dependency, FactoryDependency)
                and dependency.dependency in self.__factories)

    def maybe_debug(self, build: Hashable) -> Optional[DependencyDebug]:
        dependency_factory = build.dependency if isinstance(build, Build) else build
        if not isinstance(dependency_factory, FactoryDependency):
            return None

        try:
            factory = self.__factories[dependency_factory.dependency]
        except KeyError:
            return None

        return DependencyDebug(
            debug_repr(build),
            singleton=factory.singleton,
            wired=[factory.function] if factory.dependency is None else [],
            dependencies=([factory.dependency]
                          if factory.dependency is not None else []))

    def maybe_provide(self, build: Hashable, container: Container
                      ) -> Optional[DependencyInstance]:
        dependency_factory = build.dependency if isinstance(build, Build) else build
        if not isinstance(dependency_factory, FactoryDependency):
            return None

        try:
            factory = self.__factories[dependency_factory.dependency]
        except KeyError:
            return None

        if factory.function is None:
            f = container.provide(factory.dependency)
            assert f.singleton, "factory dependency is expected to be a singleton"
            factory.function = f.value

        instance = (factory.function(**build.kwargs)
                    if isinstance(build, Build) and build.kwargs
                    else factory.function())

        return DependencyInstance(instance, singleton=factory.singleton)

    def register(self,
                 dependency: Hashable,
                 factory: Union[Callable, Dependency],
                 singleton: bool = True) -> 'FactoryDependency':
        # For now we don't support multiple factories for a single dependency.
        # Simply because I don't see a use case where it would make sense. In
        # Antidote the standard way would be to use `with_kwargs()` to customization
        # Open for discussions though, create an issue if you a use case.
        factory_dependency = FactoryDependency(dependency, weakref.ref(self))
        self._assert_not_duplicate(factory_dependency)

        if isinstance(factory, Dependency):
            self.__factories[dependency] = Factory(dependency=factory.value,
                                                   singleton=singleton)
        elif callable(factory):
            self.__factories[dependency] = Factory(singleton=singleton,
                                                   function=factory)
        else:
            raise TypeError(f"factory must be callable, not {type(factory)!r}.")

        return factory_dependency

    def debug_get_registered_factory(self, dependency: Hashable
                                     ) -> Union[Callable, Dependency]:
        factory = self.__factories[dependency]
        if factory.dependency is not None:
            return Dependency(factory.dependency)
        else:
            return factory.function


@API.private
class FactoryDependency(FinalImmutable):
    __slots__ = ('dependency', '_provider_ref')
    dependency: Hashable
    _provider_ref: 'weakref.ReferenceType[FactoryProvider]'

    def __repr__(self):
        return f"FactoryDependency({self})"

    def __antidote_debug_repr__(self):
        return str(self)

    def __str__(self):
        provider = self._provider_ref()
        dependency = debug_repr(self.dependency)
        if provider is not None:
            factory = provider.debug_get_registered_factory(self.dependency)
            return f"{dependency} @ {debug_repr(factory)}"
        # Should not happen, but we'll try to provide some debug information
        return f"{dependency} @ ???"  # pragma: no cover


@API.private
class Factory(SlotRecord):
    __slots__ = ('singleton', 'function', 'dependency')
    singleton: bool
    function: Callable
    dependency: Any

    def __init__(self,
                 singleton: bool = True,
                 function: Callable = None,
                 dependency: Any = None):
        assert function is not None or dependency is not None
        super().__init__(singleton, function, dependency)
