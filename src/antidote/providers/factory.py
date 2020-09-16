from __future__ import annotations

from typing import Any, Callable, Dict, Hashable, Optional, Union
from weakref import ref, ReferenceType

from .service import Build
from .._internal import API
from .._internal.utils import FinalImmutable, SlotRecord
from ..core import Dependency, DependencyContainer, DependencyInstance, DependencyProvider
from ..exceptions import DuplicateDependencyError


@API.private
class FactoryProvider(DependencyProvider):
    def __init__(self):
        super().__init__()
        self.__factories: Dict[Hashable, Factory] = dict()

    def __repr__(self):
        return f"{type(self).__name__}(factories={self.__factories})"

    def clone(self, keep_singletons_cache: bool) -> FactoryProvider:
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

    def provide(self, build: Hashable, container: DependencyContainer
                ) -> Optional[DependencyInstance]:
        dependency_factory = build.dependency if isinstance(build, Build) else build
        if not isinstance(dependency_factory, FactoryDependency):
            return

        try:
            factory = self.__factories[dependency_factory.dependency]
        except KeyError:
            return

        if factory.function is None:
            f = container.provide(factory.dependency)
            assert f.singleton, "factory dependency is expected to be a singleton"
            factory.function = f.instance

        instance = (factory.function(**build.kwargs)
                    if isinstance(build, Build) and build.kwargs
                    else factory.function())

        return DependencyInstance(instance, singleton=factory.singleton)

    def register(self,
                 dependency: Hashable,
                 factory: Union[Callable, Dependency],
                 singleton: bool = True) -> FactoryDependency:
        # For now we don't support multiple factories for a single dependency.
        # Simply because I don't see a use case where it would make sense. In
        # Antidote the standard way would be to use `with_kwargs()` to customization
        # Open for discussions though, create an issue if you a use case.
        if dependency in self.__factories:
            raise DuplicateDependencyError(
                dependency,
                self.__factories[dependency]
            )
        if isinstance(factory, Dependency):
            return self.__add(dependency,
                              Factory(dependency=factory.value,
                                      singleton=singleton))
        elif callable(factory):
            return self.__add(dependency, Factory(singleton=singleton,
                                                  function=factory))
        else:
            raise TypeError(f"factory must be callable, not {type(factory)!r}.")

    def __add(self, dependency: Hashable, factory: Factory):
        self.__factories[dependency] = factory
        factory_dependency = FactoryDependency(dependency, ref(self))
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
    _provider_ref: ReferenceType[FactoryProvider]

    def __repr__(self):
        provider = self._provider_ref()
        if provider is not None:
            factory = provider.debug_get_registered_factory(self.dependency)
            return f"FactoryDependency({self.dependency!r} @ {factory!r})"
        # Should not happen, but we'll try to provide some debug information
        return f"FactoryDependency({self.dependency!r} @ ???)"  # pragma: no cover


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
