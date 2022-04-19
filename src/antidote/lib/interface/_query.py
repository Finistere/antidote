from dataclasses import dataclass
from typing import Any, List, Tuple, Type

from typing_extensions import final, TypeAlias

from .predicate import (Predicate, PredicateConstraint)
from ..._internal import API

__all__ = ['ConstraintsAlias', 'Query']

ConstraintsAlias: TypeAlias = List[Tuple[Type[Predicate[Any]], PredicateConstraint[Any]]]


@API.private
@final
@dataclass(frozen=True)
class Query:
    __slots__ = ('interface', 'constraints', 'all')
    interface: type
    constraints: ConstraintsAlias
    all: bool

    def __hash__(self) -> int:
        return object.__hash__(self)
