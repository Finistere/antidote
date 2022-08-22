from __future__ import annotations

import inspect
import itertools
from dataclasses import dataclass
from typing import (
    Any,
    cast,
    Generic,
    Iterable,
    List,
    Optional,
    Sequence,
    Type,
    TYPE_CHECKING,
    TypeVar,
)

from typing_extensions import final, get_type_hints

from ..._internal import API, CachedMeta, debug_repr, extract_optional_value
from ..._internal.typing import Out
from .predicate import (
    ImplementationWeight,
    MergeablePredicateConstraint,
    NeutralWeight,
    Predicate,
    PredicateConstraint,
)
from .qualifier import QualifiedBy

if TYPE_CHECKING:
    from ._provider import ImplementationsRegistry

__all__ = [
    "ImplementationQuery",
    "Constraint",
    "ImplementationsRegistryDependency",
    "create_constraints",
    "create_conditions",
]

Weight = TypeVar("Weight", bound=ImplementationWeight)
Pred = TypeVar("Pred", bound=Predicate[Any])


@API.private
@dataclass(frozen=True)
class Constraint(Generic[Pred]):
    __slots__ = ("predicate_type", "callback")
    predicate_type: Type[Pred]
    callback: PredicateConstraint[Pred]

    def __hash__(self) -> int:
        try:
            return hash(self.callback)
        except TypeError:
            return object.__hash__(self)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Constraint)
            and other.callback == self.callback  # pyright: ignore[reportUnknownMemberType]
        )

    def __repr__(self) -> str:
        return repr(self.callback)


@API.private
@dataclass(frozen=True)
class ImplementationQuery(Generic[Out], metaclass=CachedMeta):
    __slots__ = ("interface", "constraints", "all", "__weakref__")
    interface: object
    constraints: Sequence[Constraint[Any]]
    all: bool

    def __init__(
        self,
        interface: object,
        *,
        constraints: Iterable[Constraint[Any]] = tuple(),
        all: bool = False,
    ) -> None:
        object.__setattr__(self, "interface", interface)
        object.__setattr__(self, "constraints", tuple(constraints))
        object.__setattr__(self, "all", all)

    def __repr__(self) -> str:
        out = "AllOf" if self.all else "SingleOf"
        out += f"({self.interface}"
        if self.constraints:
            out += f", constraints={self.constraints}"
        return out + ")"

    def __antidote_debug_repr__(self) -> str:
        out = f"<{'all' if self.all else 'single'}> {debug_repr(self.interface)}"
        if self.constraints:
            out += f" // {', '.join(debug_repr(c.callback) for c in self.constraints)}"
        return out

    def __antidote_dependency_hint__(self) -> Out:
        return cast(Out, self)


@API.private
@final
@dataclass(frozen=True, eq=False)
class ImplementationsRegistryDependency:
    __slots__ = ("interface",)
    interface: object

    def __antidote_dependency_hint__(self) -> ImplementationsRegistry:
        return self  # type: ignore


@API.private
def create_conditions(
    *conditions: Predicate[Weight]
    | Predicate[NeutralWeight]
    | Weight
    | NeutralWeight
    | None
    | bool,
    qualified_by: Optional[object | list[object]] = None,
) -> Sequence[Predicate[Weight] | Predicate[NeutralWeight] | Weight | NeutralWeight | None | bool]:
    result: list[
        Predicate[Weight] | Predicate[NeutralWeight] | Weight | NeutralWeight | None | bool
    ] = list(conditions)
    if qualified_by is not None:
        if isinstance(qualified_by, (list, tuple)):
            result.append(QualifiedBy(*cast(List[object], qualified_by)))
        else:
            result.append(QualifiedBy(qualified_by))
    return result


@API.private
def create_constraints(
    *_constraints: PredicateConstraint[Any],
    qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
    qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
) -> Sequence[Constraint[Any]]:
    # Validate constraints
    constraints: list[PredicateConstraint[Any]] = []
    for constraint in _constraints:
        if not (callable(constraint) and isinstance(constraint, PredicateConstraint)):
            raise TypeError(f"Expected a PredicateConstraint, not a {type(constraint)}")
        constraints.append(constraint)

    # Create constraints from kwargs
    if qualified_by is not None:
        if isinstance(qualified_by, (list, tuple)):
            constraints.append(QualifiedBy(*cast(List[object], qualified_by)))
        else:
            constraints.append(QualifiedBy(qualified_by))

    if not (qualified_by_one_of is None or isinstance(qualified_by_one_of, (tuple, list))):
        raise TypeError(
            f"qualified_by_one_of should be None or a list, not {type(qualified_by_one_of)!r}"
        )
    if qualified_by_one_of:
        constraints.append(QualifiedBy.one_of(*qualified_by_one_of))

    # Remove duplicates and combine constraints when possible
    constraints_groups: dict[
        Type[PredicateConstraint[Any]], list[PredicateConstraint[Any]]
    ] = dict()
    for constraint in constraints:
        cls = type(constraint)
        previous = constraints_groups.setdefault(cls, [])
        if issubclass(cls, MergeablePredicateConstraint) and len(previous) > 0:
            cls = cast(Type[MergeablePredicateConstraint[Any]], cls)  # type: ignore
            previous[0] = cls.merge(
                cast(MergeablePredicateConstraint[Any], previous[0]),
                cast(MergeablePredicateConstraint[Any], constraint),
            )
        else:
            previous.append(constraint)

    # Extract associated predicate from the type hints
    return [
        Constraint(predicate_type=extract_predicate_type(constraint), callback=constraint)
        for constraint in itertools.chain.from_iterable(constraints_groups.values())
    ]


@API.private
def extract_predicate_type(constraint: PredicateConstraint[Pred]) -> Type[Pred]:
    func: Any = constraint if inspect.isfunction(constraint) else constraint.__call__
    parameters = list(inspect.signature(func).parameters.values())
    if not parameters:
        raise TypeError(f"Missing an argument for the predicate on {constraint}")
    first_arg_name = parameters[0].name
    predicate_type_hint = get_type_hints(func).get(first_arg_name)
    if predicate_type_hint is None:
        raise TypeError(
            f"First argument of {constraint} must have "
            f"an optional Predicate type hint. It defines which predicate will be "
            f"injected"
        )

    predicate_type = extract_optional_value(predicate_type_hint)
    if not (isinstance(predicate_type, type) and issubclass(predicate_type, Predicate)):
        raise TypeError(
            f"First argument of {constraint} must have "
            f"an optional Predicate type hint. It defines which predicate will be "
            f"injected"
        )
    return cast(Type[Pred], predicate_type)
