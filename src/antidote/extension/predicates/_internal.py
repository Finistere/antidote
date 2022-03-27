from __future__ import annotations

import inspect
import itertools
from typing import Any, cast, get_args, get_origin, get_type_hints, Optional, Type, TypeVar, Union

from ._provider import ConstraintsAlias, InterfaceProvider
from .predicate import Predicate, PredicateConstraint
from .qualifier import QualifiedBy
from ...core import inject
from ...core.exceptions import DuplicateDependencyError

C = TypeVar('C', bound=type)


def create_constraints(*_constraints: PredicateConstraint[Any],
                       qualified_by: Optional[list[object]] = None,
                       qualified_by_one_of: Optional[list[object]] = None,
                       qualified_by_instance_of: Optional[type] = None
                       ) -> ConstraintsAlias:
    # Validate constraints
    constraints: list[PredicateConstraint[Any]] = []
    for constraint in _constraints:
        if not isinstance(constraint, PredicateConstraint):
            raise TypeError(f"Expected a PredicateConstraint, not a {type(constraint)}")
        constraints.append(constraint)

    # Create constraints from kwargs
    if not (qualified_by is None or isinstance(qualified_by, list)):
        raise TypeError(f"qualified_by should be None or a list, not {type(qualified_by)!r}")
    if qualified_by:
        constraints.append(QualifiedBy(*qualified_by))

    if not (qualified_by_one_of is None or isinstance(qualified_by_one_of, list)):
        raise TypeError(f"qualified_by_one_of should be None or a list, "
                        f"not {type(qualified_by_one_of)!r}")
    if qualified_by_one_of:
        constraints.append(QualifiedBy.one_of(*qualified_by_one_of))

    if qualified_by_instance_of is not None:
        constraints.append(QualifiedBy.instance_of(qualified_by_instance_of))

    # Remove duplicates and combine constraints when possible
    constraints_groups: dict[Type[PredicateConstraint], list[PredicateConstraint]] = dict()
    for constraint in set(constraints):
        tpe = type(constraint)
        previous = constraints_groups.setdefault(tpe, [])
        if previous and tpe.__and__ != PredicateConstraint.__and__:
            previous[0] &= constraint
        else:
            previous.append(constraint)

    # Extract associated predicate from the type hints
    result: ConstraintsAlias = list()
    for contraint in itertools.chain.from_iterable(constraints_groups.values()):
        predicate_type_hint = get_type_hints(contraint.__call__).get('predicate')
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
        result.append((predicate_type, contraint))

    return result


@inject
def register_interface(__interface: C,
                       *,
                       provider: InterfaceProvider = inject.me()
                       ) -> C:
    if not (isinstance(__interface, type) and inspect.isclass(__interface)):
        raise TypeError(f"Expected a class for the interface, got a {type(__interface)!r}")

    provider.register(__interface)
    return __interface


@inject
def register_implementation(*,
                            interface: type,
                            implementation: C,
                            predicates: list[Predicate],
                            provider: InterfaceProvider = inject.me()
                            ) -> C:
    from ...service import service
    if not (isinstance(interface, type) and inspect.isclass(interface)):
        raise TypeError(f"Expected a class for the interface, got a {type(interface)!r}")
    if not (isinstance(implementation, type) and inspect.isclass(implementation)):
        raise TypeError(f"Expected a class for the implementation, got a {type(implementation)!r}")

    # Remove duplicates and combine predicates when possible
    distinct_predicates: dict[Type[Predicate], Predicate] = dict()
    for predicate in set(predicates):
        key = type(predicate)
        previous = distinct_predicates.get(key)
        if previous is not None:
            distinct_predicates[key] = previous & predicate
        else:
            distinct_predicates[key] = predicate

    provider.register_implementation(
        interface=interface,
        dependency=implementation,
        predicates=list(distinct_predicates.values())
    )

    try:
        return service(implementation)
    except DuplicateDependencyError:
        return implementation
