from __future__ import annotations

import inspect
from typing import Any, Callable, cast, Generic, List, Optional, overload, Type, TypeVar, Union

from typing_extensions import final

from ._internal import create_constraints, register_implementation, register_interface
from ._provider import InterfaceProvider, Query
from .predicate import AnyPredicateWeight, Predicate, PredicateConstraint
from .qualifier import QualifiedBy
from ..._internal.utils import FinalImmutable
from ..._internal.utils.meta import Singleton
from ...core import Dependency, inject

Itf = TypeVar('Itf', bound=type)
C = TypeVar('C', bound=type)
T = TypeVar('T')
Weight = TypeVar('Weight', bound=AnyPredicateWeight)


def register_interface_provider() -> None:
    from antidote import world
    world.provider(InterfaceProvider)


@final
class Interface(Singleton):
    @overload
    def __call__(self, klass: C) -> C:
        ...  # pragma: no cover

    @overload
    def __call__(self) -> Callable[[C], C]:
        ...  # pragma: no cover

    def __call__(self, klass: Optional[C] = None) -> Union[C, Callable[[C], C]]:
        return klass and register_interface(klass) or register_interface

    def __getitem__(self, klass: Type[T]) -> QueryBuilder[T]:
        return QueryBuilder(klass)


class ImplementsWithPredicates(Generic[Itf]):
    def __init__(self,
                 __interface: Itf,
                 predicates: Optional[list[Predicate[Weight]]] = None
                 ) -> None:
        self._interface = __interface
        self.__predicates = predicates or []

    def __call__(self, klass: C) -> C:
        register_implementation(
            interface=self._interface,
            implementation=klass,
            predicates=self.__predicates
        )
        return klass


@final
class implements(ImplementsWithPredicates[Itf]):
    def __init__(self, __interface: Itf) -> None:
        super().__init__(__interface)

    def when(self,
             *_predicates: Predicate[Weight],
             qualified_by: Optional[list[object]] = None
             ) -> ImplementsWithPredicates[Itf]:
        predicates = list(_predicates)
        if qualified_by is not None:
            predicates.append(QualifiedBy(*qualified_by))
        return ImplementsWithPredicates(self._interface, predicates)


@final
class QueryBuilder(FinalImmutable, Generic[T]):
    __slots__ = ('interface',)
    interface: Type[T]

    @inject
    def __init__(self, interface: Type[T], provider: InterfaceProvider = inject.me()) -> None:
        if not (isinstance(interface, type) and inspect.isclass(interface)):
            raise TypeError(f"Expected a class, got a {type(interface)!r}")
        if not provider.has_interface(interface):
            raise ValueError(f"Interface {interface} was not decorated with @interface.")
        super().__init__(interface)

    def all(self,
            *constraints: PredicateConstraint[Any],
            qualified_by: Optional[list[object]] = None,
            qualified_by_one_of: Optional[list[object]] = None,
            qualified_by_instance_of: Optional[type] = None
            ) -> Dependency[list[T]]:
        query = Query(
            interface=self.interface,
            constraints=create_constraints(
                *constraints,
                qualified_by=qualified_by,
                qualified_by_one_of=qualified_by_one_of,
                qualified_by_instance_of=qualified_by_instance_of
            ),
            all=True
        )
        return cast(Dependency[List[T]], query)

    def single(self,
               *constraints: PredicateConstraint[Any],
               qualified_by: Optional[list[object]] = None,
               qualified_by_one_of: Optional[list[object]] = None,
               qualified_by_instance_of: Optional[type] = None
               ) -> Dependency[T]:
        query = Query(
            interface=self.interface,
            constraints=create_constraints(
                *constraints,
                qualified_by=qualified_by,
                qualified_by_one_of=qualified_by_one_of,
                qualified_by_instance_of=qualified_by_instance_of
            ),
            all=False
        )
        return cast(Dependency[T], query)


interface = Interface()
