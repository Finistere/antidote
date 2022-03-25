from __future__ import annotations

import bisect
from typing import Any, cast, Generic, List, Optional, Sequence, Tuple, Type, TypeVar, Union

from typing_extensions import final, TypeAlias

from .predicate import (NeutralWeight,
                        Predicate, PredicateConstraint,
                        PredicateWeight)
from ..._internal import API
from ..._internal.utils import debug_repr, FinalImmutable
from ..._internal.utils.slots import SlotsRepr
from ...core import Container, DependencyDebug, DependencyValue, does_not_freeze, Provider
from ...core.utils import DebugInfoPrefix

T = TypeVar('T')
Weight = TypeVar('Weight', bound=PredicateWeight)
ConstraintsAlias: TypeAlias = List[Tuple[Type[Predicate[Any]], PredicateConstraint[Any]]]


@API.private
@final
class Query(FinalImmutable):
    __slots__ = ('interface', 'constraints', 'all')
    interface: type
    constraints: ConstraintsAlias
    all: bool

    def __init__(self,
                 *,
                 interface: type,
                 constraints: ConstraintsAlias,
                 all: bool
                 ) -> None:
        super().__init__(interface, constraints, all)


class InterfaceProvider(Provider[Query]):
    def __init__(self) -> None:
        super().__init__()
        self.__implementations: dict[type, list[ImplementationNode[Any]]] = dict()

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
            implementations = reversed(self.__implementations[dependency.interface])
        except KeyError:
            return None

        if dependency.all:
            values: list[object] = []
            for impl in implementations:
                if impl.match(dependency.constraints):
                    values.append(container.get(impl.dependency))
            return DependencyValue(values)
        else:
            for impl in implementations:
                if impl.match(dependency.constraints):
                    left_impl = impl
                    while left_impl.same_weight_as_left:
                        left_impl = next(implementations)
                        if left_impl.match(dependency.constraints):
                            raise RuntimeError(
                                f"Multiple implementations match the interface "
                                f"{dependency.interface!r} for the constraints "
                                f"{dependency.constraints}: "
                                f"{impl.dependency!r} and {left_impl.dependency!r}")

                    return DependencyValue(container.get(impl.dependency))

        return None

    def debug(self, dependency: Query) -> DependencyDebug:
        if not isinstance(dependency, Query):
            assert isinstance(dependency, type)
            dependency = Query(
                interface=dependency,
                constraints=[],
                all=False
            )

        values: list[ImplementationNode[Any]] = []
        for impl in reversed(self.__implementations[dependency.interface]):
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
        self.__implementations[interface] = list()

    def register_implementation(self,
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

        node = ImplementationNode(
            dependency=dependency,
            predicates=predicates,
            weight=weight
        )
        implementations = self.__implementations[interface]
        pos = bisect.bisect_right(implementations, node)
        node.same_weight_as_left = pos > 0 and not (implementations[pos - 1] < node)
        implementations.insert(pos, node)


@API.private
@final
class ImplementationNode(SlotsRepr, Generic[Weight]):
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

    def __lt__(self, other: ImplementationNode[Weight]) -> bool:
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
