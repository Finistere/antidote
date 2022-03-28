from __future__ import annotations

import bisect
from typing import Any, Callable, cast, List, Optional, Tuple, TypeVar, Union

from typing_extensions import final, TypeAlias

from .predicate import AntidotePredicateWeight, AnyPredicateWeight, Predicate
from ..._internal.utils import debug_repr, FinalImmutable
from ..._internal.utils.slots import SlotsRepr
from ...core import Container, DependencyDebug, DependencyValue, Provider
from ...core.exceptions import DependencyInstantiationError
from ...core.utils import DebugInfoPrefix

T = TypeVar('T')
ConstraintsAlias: TypeAlias = List[Tuple[type, Callable[[Optional[Any]], bool]]]


class InterfaceProvider(Provider[Union[type, 'Query']]):
    def __init__(self) -> None:
        super().__init__()
        self.__implementations: dict[type, list[ImplementationNode]] = dict()

    def clone(self: InterfaceProvider, keep_singletons_cache: bool) -> InterfaceProvider:
        provider = InterfaceProvider()
        provider.__implementations = {
            key: value.copy()
            for key, value in self.__implementations.items()
        }

        return provider

    def exists(self, dependency: object) -> bool:
        return (dependency in self.__implementations
                or (isinstance(dependency, Query)
                    and dependency.interface in self.__implementations))

    def maybe_provide(self,
                      dependency: object,
                      container: Container
                      ) -> Optional[DependencyValue]:
        if not isinstance(dependency, Query):
            dependency = Query(
                # not always true, but we won't go far if it's a lie.
                interface=cast(type, dependency),
                constraints=list(),
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
                            raise DependencyInstantiationError(
                                f"Multiple implementations match the interface "
                                f"{dependency.interface!r} for the constraints "
                                f"{dependency.constraints}: "
                                f"{impl.dependency!r} and {left_impl.dependency!r}")

                    return DependencyValue(container.get(impl.dependency))

        return None

    def maybe_debug(self, dependency: object) -> Optional[DependencyDebug]:
        if not isinstance(dependency, Query):
            dependency = Query(
                # not always true, but we won't go far if it's a lie.
                interface=cast(type, dependency),
                constraints=list(),
                all=False
            )

        try:
            implementations = reversed(self.__implementations[dependency.interface])
        except KeyError:
            return None

        values: list[ImplementationNode] = []
        for impl in implementations:
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
                                predicates: list[Predicate]) -> None:
        if len(predicates) > 0:
            weights = [p.weight() for p in predicates]
            if any(w is None for w in weights):
                return

            start = 0
            for i, w in enumerate(weights):
                if not isinstance(w, AntidotePredicateWeight):
                    start = i
                    break

            weight = weights[start]
            for i in range(1, len(weights)):
                weight += weights[(start + i) % len(weights)]
        else:
            weight = None
        node = ImplementationNode(
            dependency=dependency,
            predicates=predicates,
            weight=weight
        )
        implementations = self.__implementations[interface]
        pos = bisect.bisect_right(implementations, node)
        node.same_weight_as_left = pos > 0 and not (implementations[pos - 1] < node)
        implementations.insert(pos, node)


@final
class ImplementationNode(SlotsRepr):
    __slots__ = ('dependency', 'predicates', 'weight', 'same_weight_as_left')
    dependency: object
    predicates: list[Predicate]
    weight: Optional[AnyPredicateWeight]
    same_weight_as_left: bool

    def __init__(self,
                 *,
                 dependency: object,
                 predicates: list[Predicate],
                 weight: Optional[Any]
                 ) -> None:
        self.dependency = dependency
        self.predicates = predicates
        self.weight = weight

    def __lt__(self, other: ImplementationNode) -> bool:
        if other.weight is None:
            return False
        elif self.weight is None:
            return other.weight is not None
        return self.weight < other.weight

    def match(self, constraints: ConstraintsAlias) -> bool:
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
