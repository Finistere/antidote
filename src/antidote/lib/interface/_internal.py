from __future__ import annotations

import itertools
from typing import Any, cast, List, Optional, Type, TypeVar, Union

from typing_extensions import get_args, get_origin, get_type_hints, TypeAlias

from ._provider import ConstraintsAlias, InterfaceProvider
from .predicate import (MergeablePredicate, MergeablePredicateConstraint, NeutralWeight, Predicate,
                        PredicateConstraint, PredicateWeight)
from ..._internal import API
from ..._internal.utils import enforce_subclass_if_possible
from ...core import inject
from ...core.exceptions import DuplicateDependencyError

__all__ = ['create_constraints', 'register_interface', 'register_implementation']

T = TypeVar('T')
C = TypeVar('C', bound=type)

P = TypeVar('P', bound=Predicate[Any])
PC = TypeVar('PC', bound=PredicateConstraint[Any])
Weight = TypeVar('Weight', bound=PredicateWeight)

AnyP: TypeAlias = Predicate[Any]
AnyPC: TypeAlias = PredicateConstraint[Any]


@API.private
def create_constraints(
        *_constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object]] = None,
        qualified_by_one_of: Optional[list[object]] = None
) -> ConstraintsAlias:
    from .qualifier import QualifiedBy

    # Validate constraints
    constraints: list[PredicateConstraint[Any]] = []
    for constraint in _constraints:
        if not isinstance(constraint, PredicateConstraint):
            raise TypeError(f"Expected a PredicateConstraint, not a {type(constraint)}")
        constraints.append(constraint)

    # Create constraints from kwargs
    if qualified_by is not None:
        if isinstance(qualified_by, list):
            constraints.append(QualifiedBy(*cast(List[object], qualified_by)))
        else:
            constraints.append(QualifiedBy(qualified_by))

    if not (qualified_by_one_of is None or isinstance(qualified_by_one_of, list)):
        raise TypeError(f"qualified_by_one_of should be None or a list, "
                        f"not {type(qualified_by_one_of)!r}")
    if qualified_by_one_of:
        constraints.append(QualifiedBy.one_of(*qualified_by_one_of))

    # Remove duplicates and combine constraints when possible
    constraints_groups: dict[
        Type[PredicateConstraint[Any]], list[PredicateConstraint[Any]]] = dict()
    for constraint in constraints:
        cls = type(constraint)
        previous = constraints_groups.setdefault(cls, [])
        if issubclass(cls, MergeablePredicateConstraint) and len(previous) > 0:
            cls = cast(Type[MergeablePredicateConstraint[Any]], cls)
            previous[0] = cls.merge(
                cast(MergeablePredicateConstraint[Any], previous[0]),
                cast(MergeablePredicateConstraint[Any], constraint)
            )
        else:
            previous.append(constraint)

    # Extract associated predicate from the type hints
    result: ConstraintsAlias = list()
    for contraint in itertools.chain.from_iterable(constraints_groups.values()):
        predicate_type_hint = get_type_hints(contraint.evaluate).get('predicate')
        if predicate_type_hint is None:
            raise TypeError(f"Missing 'predicate' argument on the predicate filter {contraint}")

        if get_origin(predicate_type_hint) is not Union:
            raise TypeError("Predicate type hint must be Optional[P] with P being a Predicate")
        args = cast(Any, get_args(predicate_type_hint))
        if not (len(args) == 2 and (isinstance(None, args[1]) or isinstance(None, args[0]))):
            raise TypeError("Predicate type hint must be Optional[P] with P being a Predicate")

        predicate_type = args[0] if isinstance(None, args[1]) else args[1]
        if not (isinstance(predicate_type, type) and issubclass(predicate_type, Predicate)):
            raise TypeError("Predicate type hint must be Optional[P] with P being a Predicate")
        result.append((cast(Type[Predicate[Any]], predicate_type), contraint))

    return result


@API.private
@inject
def register_interface(__interface: C,
                       *,
                       provider: InterfaceProvider = inject.get(InterfaceProvider)
                       ) -> C:
    if not isinstance(__interface, type):
        raise TypeError(f"Expected a class for the interface, got a {type(__interface)!r}")

    provider.register(__interface)
    return cast(C, __interface)


@API.private
@inject
def register_implementation(*,
                            interface: type,
                            implementation: C,
                            predicates: List[Union[Predicate[Weight], Predicate[NeutralWeight]]],
                            provider: InterfaceProvider = inject.get(InterfaceProvider)
                            ) -> C:
    from ...service import service

    if not isinstance(interface, type):
        raise TypeError(f"Expected a class for the interface, got a {type(interface)!r}")
    if not isinstance(implementation, type):
        raise TypeError(f"Expected a class for the implementation, got a {type(implementation)!r}")
    enforce_subclass_if_possible(implementation, interface)

    # Remove duplicates and combine predicates when possible
    distinct_predicates: dict[Type[Predicate[Any]], Predicate[Any]] = dict()
    for predicate in predicates:
        if not isinstance(predicate, Predicate):
            raise TypeError(f"Expected an instance of Predicate, not a {type(predicate)!r}")

        cls = type(predicate)
        previous = distinct_predicates.get(cls)
        if previous is not None:
            if not issubclass(cls, MergeablePredicate):
                raise RuntimeError(f"Cannot have multiple predicates of type {cls!r} "
                                   f"without declaring a reducer!")
            cls = cast(Type[MergeablePredicate[Any]], cls)
            distinct_predicates[cls] = cls.merge(
                cast(MergeablePredicate[Any], previous),
                cast(MergeablePredicate[Any], predicate)
            )
        else:
            distinct_predicates[cls] = predicate

    provider.register_implementation(
        interface=interface,
        dependency=implementation,
        predicates=list(distinct_predicates.values())
    )

    try:
        return cast(C, service(implementation))
    except DuplicateDependencyError:
        return cast(C, implementation)
