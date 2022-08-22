from __future__ import annotations

import bisect
import dataclasses
import threading
from dataclasses import dataclass
from typing import Any, cast, Generic, Iterable, List, Sequence, Type, TypeVar, Union

from typing_extensions import final

from ... import dependencyOf
from ..._internal import API, debug_repr
from ...core import (
    DebugInfoPrefix,
    DependencyDebug,
    DuplicateDependencyError,
    LifeTime,
    ProvidedDependency,
    Provider,
    ProviderCatalog,
)
from . import AmbiguousImplementationChoiceError, SingleImplementationNotFoundError
from ._internal import Constraint, ImplementationQuery, ImplementationsRegistryDependency
from .predicate import HeterogeneousWeightError, ImplementationWeight, NeutralWeight, Predicate

__all__ = ["InterfaceProvider", "ImplementationsRegistry"]

Weight = TypeVar("Weight", bound=ImplementationWeight)
NewWeight = TypeVar("NewWeight", bound=ImplementationWeight)


@API.private
@final
@dataclass(frozen=True)
class InterfaceProvider(Provider):
    __slots__ = ("__implementations",)
    __implementations: dict[object, ImplementationsRegistry]

    def __init__(
        self,
        *,
        catalog: ProviderCatalog,
        implementations: dict[object, ImplementationsRegistry] | None = None,
    ) -> None:
        super().__init__(catalog=catalog)
        object.__setattr__(
            self, f"_{type(self).__name__}__implementations", implementations or dict()
        )

    def unsafe_copy(self) -> InterfaceProvider:
        return InterfaceProvider(
            catalog=self._catalog,
            implementations={key: value.copy() for key, value in self.__implementations.items()},
        )

    def can_provide(self, dependency: object) -> bool:
        if isinstance(dependency, (ImplementationQuery, ImplementationsRegistryDependency)):
            return dependency.interface in self.__implementations
        return dependency in self.__implementations

    def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
        if isinstance(dependency, ImplementationQuery):
            query: ImplementationQuery[object] = dependency
            try:
                implementations = self.__implementations[query.interface]
            except KeyError:
                return
        else:
            if isinstance(dependency, ImplementationsRegistryDependency):
                try:
                    out.set_value(
                        self.__implementations[dependency.interface], lifetime=LifeTime.SINGLETON
                    )
                except KeyError:
                    pass
                return

            try:
                implementations = self.__implementations[dependency]
            except KeyError:
                return

            query = ImplementationQuery[object](dependency)

        get = self._catalog.__getitem__

        if query.all:
            values: list[object] = []
            for candidate in reversed(implementations.candidates_ordered_asc):
                if candidate.match(query.constraints):
                    values.append(get(candidate.implementation.dependency))
            if implementations.default_implementation is not None and not values:
                values.append(get(implementations.default_implementation.dependency))
            out.set_value(values, lifetime=LifeTime.TRANSIENT)
        else:
            candidates = reversed(implementations.candidates_ordered_asc)
            for candidate in candidates:
                if candidate.match(query.constraints):
                    left_impl = candidate
                    while left_impl.same_weight_as_left:
                        left_impl = next(candidates)
                        if left_impl.match(query.constraints):
                            raise AmbiguousImplementationChoiceError(
                                query=query,
                                a=candidate.implementation.identifier,
                                b=left_impl.implementation.identifier,
                            )

                    out.set_value(
                        get(candidate.implementation.dependency), lifetime=LifeTime.TRANSIENT
                    )
                    return
            if implementations.default_implementation is not None:
                # TODO: can be more efficient by using container.provide() when frozen for caching.
                out.set_value(
                    get(implementations.default_implementation.dependency),
                    lifetime=LifeTime.TRANSIENT,
                )
                return
            raise SingleImplementationNotFoundError(query=query)

    def maybe_debug(self, dependency: object) -> DependencyDebug | None:
        if not isinstance(dependency, ImplementationQuery):
            dependency = ImplementationQuery[object](dependency)

        try:
            implementations = self.__implementations[dependency.interface]
        except KeyError:
            return None

        values: list[CandidateImplementation[Any]] = [
            impl
            for impl in reversed(implementations.candidates_ordered_asc)
            if impl.match(dependency.constraints)
        ]

        dependencies: list[DebugInfoPrefix] = []
        for impl in values:
            dependencies.append(
                DebugInfoPrefix(
                    prefix=f"[{impl.weight}] " if len(values) > 1 else "",
                    dependency=impl.implementation.dependency,
                )
            )

        if not dependencies and implementations.default_implementation is not None:
            dependencies.append(
                DebugInfoPrefix(
                    prefix="[Default] ",
                    dependency=implementations.default_implementation.dependency,
                )
            )

        return DependencyDebug(
            description=debug_repr(cast(object, dependency)),
            lifetime="transient",
            dependencies=dependencies,
        )

    def register(self, interface: object) -> ImplementationsRegistry:
        self._catalog.raise_if_frozen()
        implementations = ImplementationsRegistry(catalog=self._catalog)
        if self.__implementations.setdefault(interface, implementations) is not implementations:
            raise DuplicateDependencyError(f"Interface {interface!r} was already defined.")
        return implementations


@API.private
@final
@dataclass(frozen=True, eq=False)
class ImplementationsRegistry:
    __slots__ = ("catalog", "lock", "candidates_ordered_asc", "default_implementation")
    catalog: ProviderCatalog
    lock: threading.RLock
    candidates_ordered_asc: tuple[CandidateImplementation[Any]]
    default_implementation: Implementation | None

    def __init__(
        self,
        *,
        catalog: ProviderCatalog,
        candidates_ordered_asc: tuple[CandidateImplementation[Any]] = cast(Any, tuple()),
        default_implementation: Implementation | None = None,
        lock: threading.RLock | None = None,
    ) -> None:
        object.__setattr__(self, "catalog", catalog)
        object.__setattr__(self, "lock", lock or threading.RLock())
        object.__setattr__(self, "candidates_ordered_asc", candidates_ordered_asc)
        object.__setattr__(self, "default_implementation", default_implementation)

    def copy(self) -> ImplementationsRegistry:
        return ImplementationsRegistry(
            catalog=self.catalog,
            candidates_ordered_asc=self.candidates_ordered_asc,
            default_implementation=self.default_implementation,
            lock=self.lock,
        )

    def set_default(self, *, identifier: object, dependency: object) -> None:
        self.catalog.raise_if_frozen()
        with self.lock:
            if self.default_implementation is not None:
                raise RuntimeError(
                    f"Default dependency already defined as "
                    f"{self.default_implementation.identifier!r}"
                )
            object.__setattr__(
                self,
                "default_implementation",
                Implementation(identifier=identifier, dependency=dependencyOf(dependency).wrapped),
            )

    def replace(
        self, *, current_identifier: object, new_identifier: object, new_dependency: object
    ) -> bool:
        self.catalog.raise_if_frozen()
        with self.lock:
            new_implementation = Implementation(
                identifier=new_identifier, dependency=dependencyOf(new_dependency).wrapped
            )
            for pos, candidate in enumerate(self.candidates_ordered_asc):
                if candidate.implementation.identifier == current_identifier:
                    candidates = list(self.candidates_ordered_asc)
                    candidates[pos] = dataclasses.replace(
                        candidate, implementation=new_implementation
                    )
                    object.__setattr__(self, "candidates_ordered_asc", tuple(candidates))
                    return True
            if (
                self.default_implementation is not None
                and self.default_implementation.identifier == current_identifier
            ):
                object.__setattr__(self, "default_implementation", new_implementation)
                return True
        return False

    def add(
        self,
        *,
        identifier: object,
        dependency: object,
        predicates: Sequence[Predicate[Weight] | Predicate[NeutralWeight]],
        weights: Sequence[Weight],
    ) -> None:
        self.catalog.raise_if_frozen()
        maybe_candidate = CandidateImplementation.create(
            identifier=identifier,
            dependency=dependencyOf(dependency).wrapped,
            predicates=predicates,
            weights=weights,
        )

        if maybe_candidate is not None:
            with self.lock:
                self.__unsafe_add_candidate(maybe_candidate)

    def __unsafe_add_candidate(self, candidate: CandidateImplementation[Any]) -> None:
        if not self.candidates_ordered_asc:
            object.__setattr__(self, "candidates_ordered_asc", (candidate,))
            return

        first = self.candidates_ordered_asc[0]
        if isinstance(first.weight, NeutralWeight) and not isinstance(
            candidate.weight, NeutralWeight
        ):
            # Fix all weights at once.
            w_type: Type[ImplementationWeight] = type(candidate.weight)
            candidates = [
                c.with_weight_type(weight_type=w_type) for c in self.candidates_ordered_asc
            ]
        else:
            candidates = list(self.candidates_ordered_asc)
            if not isinstance(first.weight, NeutralWeight) and isinstance(
                candidate.weight, NeutralWeight
            ):
                candidate = candidate.with_weight_type(type(first.weight))
            elif type(candidate.weight) != type(first.weight):  # noqa: E721
                raise HeterogeneousWeightError(candidate.weight, first.weight)

        pos = bisect.bisect_right(candidates, candidate)
        if pos > 0 and not (candidates[pos - 1] < candidate):
            candidate = dataclasses.replace(candidate, same_weight_as_left=True)
        candidates.insert(pos, candidate)
        object.__setattr__(self, "candidates_ordered_asc", tuple(candidates))


@API.private
@final
@dataclass(frozen=True, eq=False)
class Implementation:
    __slots__ = ("identifier", "dependency")
    identifier: object
    dependency: object


@API.private
@final
@dataclass(frozen=True, eq=False)
class CandidateImplementation(Generic[Weight]):
    __slots__ = ("implementation", "predicates", "weight", "same_weight_as_left")
    implementation: Implementation
    predicates: Sequence[Predicate[Weight] | Predicate[NeutralWeight]]
    weight: Weight
    same_weight_as_left: bool

    def with_weight_type(self, weight_type: Type[NewWeight]) -> CandidateImplementation[NewWeight]:
        assert isinstance(self.weight, NeutralWeight)
        return cast(
            CandidateImplementation[NewWeight],
            dataclasses.replace(
                self,
                weight=sum(
                    (weight_type.of_neutral_predicate(p) for p in self.predicates),
                    weight_type.neutral(),
                ),
            ),
        )

    @classmethod
    def create(
        cls,
        *,
        identifier: object,
        dependency: object,
        predicates: Sequence[Predicate[Weight] | Predicate[NeutralWeight]],
        weights: Sequence[Weight],
    ) -> CandidateImplementation[Weight] | None:
        maybe_predicate_weights = [p.weight() for p in predicates]
        if any(w is None for w in maybe_predicate_weights):
            return None

        predicate_weights = cast(List[Union[Weight, NeutralWeight]], maybe_predicate_weights)
        # if current weight is neutral, search for a non-neutral weight
        start = -1
        for i, w in enumerate(predicate_weights):
            if not isinstance(w, NeutralWeight):
                start = i
                break

        iter_weights = iter(weights)
        # If we found any non-neutral weight, add them:
        if start >= 0:
            n = len(predicate_weights) - 1
            weight = cast(Weight, predicate_weights[start])
        else:
            n = len(predicate_weights)
            weight = cast(Weight, next(iter_weights) if weights else NeutralWeight())

        for i in range(1, n + 1):
            pos = (start + i) % len(predicate_weights)
            w = predicate_weights[pos]
            if isinstance(w, NeutralWeight):
                weight += weight.of_neutral_predicate(predicates[pos])
            elif type(w) != type(weight):
                raise HeterogeneousWeightError(w, weight)
            else:
                weight += w

        for w in iter_weights:
            assert not isinstance(w, NeutralWeight)
            if type(w) != type(weight):
                raise HeterogeneousWeightError(w, weight)
            else:
                weight += w

        return cls(
            implementation=Implementation(identifier=identifier, dependency=dependency),
            predicates=predicates,
            weight=weight,
            same_weight_as_left=False,
        )

    def __lt__(self, other: CandidateImplementation[Weight]) -> bool:
        return self.weight < other.weight

    def match(self, constraints: Iterable[Constraint[Any]]) -> bool:
        for contraint in constraints:
            at_least_one = False
            for predicate in self.predicates:
                if isinstance(predicate, contraint.predicate_type):
                    at_least_one = True
                    if not contraint.callback(predicate):
                        return False
            if not at_least_one:
                if not contraint.callback(None):
                    return False
        return True
