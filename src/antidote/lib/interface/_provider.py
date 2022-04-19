from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Any, cast, Generic, Iterator, List, Optional, Sequence, TypeVar, Union

from typing_extensions import final

from ._query import ConstraintsAlias, Query
from .predicate import (NeutralWeight,
                        Predicate, PredicateWeight)
from ..._internal import API
from ..._internal.utils import debug_repr
from ...core import Container, DependencyDebug, DependencyValue, does_not_freeze, Provider
from ...core.utils import DebugInfoPrefix

__all__ = ['InterfaceProvider']

T = TypeVar('T')
Weight = TypeVar('Weight', bound=PredicateWeight)


class InterfaceProvider(Provider[Query]):
    def __init__(self) -> None:
        super().__init__()
        self.__implementations: dict[type, Implementations] = dict()

    def clone(self: InterfaceProvider, keep_singletons_cache: bool) -> InterfaceProvider:
        provider = InterfaceProvider()
        provider.__implementations = {
            key: value.copy()
            for key, value in self.__implementations.items()
        }

        return provider

    @does_not_freeze
    def has_interface(self, tpe: type) -> bool:
        return tpe in self.__implementations

    def exists(self, dependency: object) -> bool:
        return (dependency in self.__implementations
                or (isinstance(dependency, Query)
                    and dependency.interface in self.__implementations))

    def maybe_provide(self,
                      dependency: object,
                      container: Container
                      ) -> Optional[DependencyValue]:
        if not isinstance(dependency, Query):
            if not isinstance(dependency, type):
                return None
            dependency = Query(
                interface=dependency,
                constraints=[],
                all=False
            )

        try:
            implementations = self.__implementations[dependency.interface]
        except KeyError:
            return None

        if dependency.all:
            values: list[object] = []
            for impl in implementations.candidates:
                if impl.match(dependency.constraints):
                    values.append(container.get(impl.dependency))
            if implementations.default_dependency is not None:
                values.append(container.get(implementations.default_dependency))
            return DependencyValue(values)
        else:
            candidates = implementations.candidates
            for impl in candidates:
                if impl.match(dependency.constraints):
                    left_impl = impl
                    while left_impl.same_weight_as_left:
                        left_impl = next(candidates)
                        if left_impl.match(dependency.constraints):
                            raise RuntimeError(
                                f"Multiple implementations match the interface "
                                f"{dependency.interface!r} for the constraints "
                                f"{dependency.constraints}: "
                                f"{impl.dependency!r} and {left_impl.dependency!r}")

                    return DependencyValue(container.get(impl.dependency))
            if implementations.default_dependency is not None:
                # TODO: can be more efficient by using container.provide() when frozen.
                return DependencyValue(container.get(implementations.default_dependency))

        return None

    def debug(self, dependency: Query) -> DependencyDebug:
        if not isinstance(dependency, Query):
            assert isinstance(dependency, type)
            dependency = Query(
                interface=dependency,
                constraints=[],
                all=False
            )

        implementations = self.__implementations[dependency.interface]
        values: list[Implementation[Any]] = []
        for impl in implementations.candidates:
            if impl.match(dependency.constraints):
                values.append(impl)

        if not dependency.all and len(values) > 0:
            heaviest = values[0]
            values = [
                impl
                for impl in values
                if not (impl < heaviest)
            ]

        return DependencyDebug(
            f"Interface {debug_repr(dependency.interface)}",
            dependencies=[
                DebugInfoPrefix(
                    prefix=f"[{impl.weight}] " if len(values) > 1 else "",
                    dependency=impl.dependency
                )
                for impl in values
            ]
        )

    def register(self, interface: type) -> None:
        self.__implementations[interface] = Implementations()

    def override_implementation(self,
                                *,
                                interface: type,
                                existing_dependency: object,
                                new_dependency: object
                                ) -> bool:
        overridden = False
        implementations = self.__implementations[interface]
        for impl in implementations.candidates:
            if impl.dependency == existing_dependency:
                impl.dependency = new_dependency
                overridden = True
        if implementations.default_dependency is existing_dependency:
            implementations.default_dependency = new_dependency
            overridden = True
        return overridden

    def register_default_implementation(self,
                                        interface: type,
                                        dependency: type
                                        ) -> None:
        implementations = self.__implementations[interface]
        if implementations.default_dependency is not None:
            raise RuntimeError(f"Default dependency already defined as "
                               f"{implementations.default_dependency!r}")
        self.__implementations[interface].default_dependency = dependency

    def register_implementation(self,
                                *,
                                interface: type,
                                dependency: object,
                                predicates: list[Predicate[Any]]
                                ) -> None:
        weight: PredicateWeight = NeutralWeight()
        if len(predicates) > 0:
            maybe_weights = [p.weight() for p in predicates]
            if any(w is None for w in maybe_weights):
                return

            weights = cast(List[PredicateWeight], maybe_weights)
            start = 0
            for i, w in enumerate(weights):
                if not isinstance(w, NeutralWeight):
                    start = i
                    break

            weight = weights[start]
            for i in range(1, len(weights)):
                pos = (start + i) % len(weights)
                w = weights[pos]
                if isinstance(w, NeutralWeight):
                    weight += weight.of_neutral(predicates[pos])
                else:
                    weight += w

        self.__implementations[interface].add_candidate(Implementation(
            dependency=dependency,
            predicates=predicates,
            weight=weight
        ))


@API.private
@final
@dataclass
class Implementations:
    __candidates: list[Implementation[Any]] = field(default_factory=list)
    default_dependency: Optional[object] = field(default=None)

    def add_candidate(self, impl: Implementation[Any]) -> None:
        pos = bisect.bisect_right(self.__candidates, impl)
        impl.same_weight_as_left = pos > 0 and not (self.__candidates[pos - 1] < impl)
        self.__candidates.insert(pos, impl)

    @property
    def candidates(self) -> Iterator[Implementation[Any]]:
        return reversed(self.__candidates)

    def copy(self) -> Implementations:
        return Implementations(
            self.__candidates.copy(),
            self.default_dependency
        )


@API.private
@final
@dataclass(init=False)
class Implementation(Generic[Weight]):
    __slots__ = ('dependency', 'predicates', 'weight', 'same_weight_as_left')
    dependency: object
    predicates: Sequence[Union[Predicate[Weight], Predicate[NeutralWeight]]]
    weight: Weight | NeutralWeight
    same_weight_as_left: bool

    def __init__(self,
                 *,
                 dependency: object,
                 predicates: list[Predicate[Weight]],
                 weight: Weight | NeutralWeight
                 ) -> None:
        self.dependency = dependency
        self.predicates = predicates
        self.weight = weight

    def __lt__(self, other: Implementation[Weight]) -> bool:
        if isinstance(self.weight, NeutralWeight) ^ isinstance(other.weight, NeutralWeight):
            if not isinstance(self.weight, NeutralWeight):
                real_weight: Weight = self.weight
                neutral_impl = other
            else:
                # Helping pyright
                assert not isinstance(other.weight, NeutralWeight)
                neutral_impl = self
                real_weight = other.weight
            if len(neutral_impl.predicates) > 0:
                weight: Weight = real_weight.of_neutral(neutral_impl.predicates[0])
                for p in neutral_impl.predicates[1:]:
                    weight += real_weight.of_neutral(p)
                neutral_impl.weight = weight
            else:
                neutral_impl.weight = real_weight.of_neutral(None)
        return cast(Weight, self.weight) < cast(Weight, other.weight)

    def match(self, constraints: ConstraintsAlias) -> bool:
        for tpe, constraint in constraints:
            at_least_one = False
            for predicate in self.predicates:
                if isinstance(predicate, tpe):
                    at_least_one = True
                    if not constraint.evaluate(predicate):
                        return False
            if not at_least_one:
                if not constraint.evaluate(None):
                    return False
        return True
