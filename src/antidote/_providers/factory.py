from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Callable, Dict, Hashable, List, Optional

from .service import Parameterized
from .._internal import API
from .._internal.utils import debug_repr, FinalImmutable
from ..core import (Container, DependencyDebug, DependencyValue, does_not_freeze, Provider,
                    Scope)


@API.private
class FactoryProvider(Provider[Hashable]):
    def __init__(self) -> None:
        super().__init__()
        self.__factory_to_dependency: dict[object, FactoryDependency] = dict()
        self.__factories: Dict[FactoryDependency, Factory] = dict()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(factories={list(self.__factories.keys())})"

    def clone(self, keep_singletons_cache: bool) -> FactoryProvider:
        p = FactoryProvider()
        if keep_singletons_cache:
            factories: dict[FactoryDependency, Factory] = {
                k: (f.copy() if f.dependency is not None else f)
                for k, f in self.__factories.items()
            }
        else:
            factories = {
                k: (f.copy(keep_function=False) if f.dependency is not None else f)
                for k, f in self.__factories.items()
            }
        p.__factories = factories
        p.__factory_to_dependency = {
            factory_dependency.factory: factory_dependency
            for factory_dependency in factories.keys()
        }
        return p

    def exists(self, dependency: Hashable) -> bool:
        # For now we don't support multiple factories for a single dependency. Neither
        # is sharing the dependency with another provider. Simply because I don't see a
        # use case where it would make sense.
        # Open for discussions though, create an issue if you a use case.
        if isinstance(dependency, Parameterized):
            dependency = dependency.wrapped
        return (isinstance(dependency, FactoryDependency)
                and dependency in self.__factories)

    def maybe_debug(self, dependency: Hashable) -> Optional[DependencyDebug]:
        dependency_factory = (dependency.wrapped
                              if isinstance(dependency, Parameterized)
                              else dependency)
        if not isinstance(dependency_factory, FactoryDependency):
            return None

        try:
            factory = self.__factories[dependency_factory]
        except KeyError:
            return None

        dependencies: List[object] = []
        wired: List[Callable[..., object]] = []
        if factory.function is None:
            dependencies.append(factory.dependency)
            if isinstance(factory.dependency, type) \
                    and inspect.isclass(factory.dependency):
                wired.append(factory.dependency.__call__)
        else:
            wired.append(factory.function)

        return DependencyDebug(debug_repr(dependency),
                               scope=factory.scope,
                               wired=wired,
                               dependencies=dependencies)

    def maybe_provide(self, dependency: Hashable, container: Container
                      ) -> Optional[DependencyValue]:
        dependency_factory = (dependency.wrapped
                              if isinstance(dependency, Parameterized)
                              else dependency)
        if not isinstance(dependency_factory, FactoryDependency):
            return None

        try:
            factory = self.__factories[dependency_factory]
        except KeyError:
            return None

        if factory.function is None:
            f = container.provide(factory.dependency)
            assert f.is_singleton(), "factory dependency is expected to be a singleton"
            assert callable(f.unwrapped)
            factory.function = f.unwrapped

        if isinstance(dependency, Parameterized):
            instance: object = factory.function(**dependency.parameters)
        else:
            instance = factory.function()

        return DependencyValue(instance, scope=factory.scope)

    @does_not_freeze
    def get_dependency_of(self, factory: object) -> FactoryDependency:
        try:
            return self.__factory_to_dependency[factory]
        except KeyError:
            raise ValueError(f"Factory {factory!r} has never been declared.")

    def register(self,
                 output: type,
                 *,
                 scope: Optional[Scope],
                 factory: Optional[Callable[..., object]] = None,
                 factory_dependency: Optional[object] = None
                 ) -> FactoryDependency:
        assert inspect.isclass(output) \
               and (factory is None or factory_dependency is None) \
               and (factory is None or callable(factory)) \
               and (isinstance(scope, Scope) or scope is None)

        dependency = FactoryDependency(
            output=output,
            factory=factory or factory_dependency
        )
        self._assert_not_duplicate(dependency)

        if factory_dependency:
            self.__factories[dependency] = Factory(scope=scope,
                                                   function=None,
                                                   dependency=factory_dependency)
        else:
            self.__factories[dependency] = Factory(scope=scope,
                                                   function=factory,
                                                   dependency=None)
        self.__factory_to_dependency[dependency.factory] = dependency
        return dependency


@API.private
class FactoryDependency(FinalImmutable):
    __slots__ = ('output', 'factory', '__hash')
    output: type
    factory: object
    __hash: int

    def __init__(self, *, output: type, factory: object):
        super().__init__(output, factory, hash((output, factory)))

    def __repr__(self) -> str:
        return f"FactoryDependency({self})"

    def __antidote_debug_repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"{debug_repr(self.output)} @ {debug_repr(self.factory)}"

    # Custom hash & eq necessary to find duplicates
    def __hash__(self) -> int:
        return self.__hash

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, FactoryDependency)
                and self.__hash == other.__hash
                and (self.output is other.output
                     or self.output == other.output)
                and (self.factory is other.factory
                     or self.factory == other.factory))  # noqa


@API.private
@dataclass
class Factory:
    __slots__ = ('scope', 'function', 'dependency')
    scope: Optional[Scope]
    dependency: Optional[Hashable]
    function: Optional[Callable[..., object]]

    def __post_init__(self) -> None:
        assert self.function is not None or self.dependency is not None

    def copy(self, keep_function: bool = True) -> Factory:
        return Factory(scope=self.scope,
                       function=self.function if keep_function else None,
                       dependency=self.dependency)
