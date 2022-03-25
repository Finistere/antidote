from __future__ import annotations

import bisect
from typing import Any, Callable, cast, List, Optional, Type, TypeVar

from .predicate import Predicate, PredicateWeight
from ..._internal.utils import FinalImmutable
from ...core import Container, Dependency, DependencyDebug, DependencyValue, Provider

T = TypeVar('T')


class InterfaceProvider(Provider[type]):
    def __init__(self) -> None:
        super().__init__()
        self.__implementations: dict[type, list[Implementation]] = dict()

    def clone(self: InterfaceProvider, keep_singletons_cache: bool) -> InterfaceProvider:
        provider = InterfaceProvider()
        provider.__implementations = {
            key: value.copy()
            for key, value in self.__implementations.items()
        }

        return provider

    def exists(self, dependency: type) -> bool:
        return isinstance(dependency,
                          Query) and dependency.interface in self.__implementations

    def maybe_provide(self, dependency: type, container: Container) -> Optional[DependencyValue]:
        if not isinstance(dependency, Query):
            return

        try:
            implementations = self.__implementations[dependency.interface]
        except KeyError:
            return

        if dependency.single:
            for impl in implementations:
                if impl.match(dependency.constraints):
                    return DependencyValue(impl)
        else:
            values = []
            for impl in implementations:
                if impl.match(dependency.constraints):
                    values.append(impl)
            return DependencyValue(values)

    def maybe_debug(self, dependency: type) -> Optional[DependencyDebug]:
        pass

    def register(self, interface: type) -> None:
        self.__implementations[interface] = list()

    def register_implementation(self,
                                interface: type,
                                dependency: object,
                                predicates: list[Predicate]) -> None:
        implementations = self.__implementations[interface]
        bisect.insort(implementations,
                      Implementation(dependency, predicates),
                      key=lambda impl: -impl.weight)


class Implementation(FinalImmutable):
    __slots__ = ('dependency', 'predicates', 'weight')
    dependency: object
    predicates: list[Predicate]
    weight: PredicateWeight

    def __init__(self, dependency: object, predicates: list[Predicate]) -> None:
        super().__init__(
            dependency=dependency,
            predicates=predicates,
            weight=sum(p.weight for p in predicates)
        )

    def match(self, constraints: list[tuple[type, Callable[[Optional[Any]], bool]]]) -> bool:
        for tpe, constraint in constraints:
            at_least_one = False
            for predicate in self.predicates:
                if isinstance(predicate, tpe):
                    at_least_one = True
                    if not constraint(predicate):
                        return False
            if not at_least_one:
                if not constraint(None):
                    return False
        return True


class Query(FinalImmutable):
    interface: type
    constraints: list[tuple[type, Callable[[Optional[Any]], bool]]]
    single: bool

    @classmethod
    def all(cls,
            interface: Type[T],
            constraints: list[tuple[type, Callable[[Optional[Any]], bool]]]
            ) -> Dependency[list[T]]:
        return cast(Dependency[List[T]],
                    cls(interface=interface, constraints=constraints, single=False))

    @classmethod
    def single(cls,
               interface: Type[T],
               constraints: list[tuple[type, Callable[[Optional[Any]], bool]]]
               ) -> Dependency[T]:
        return cast(Dependency[T],
                    cls(interface=interface, constraints=constraints, single=True))
