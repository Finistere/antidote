from __future__ import annotations

import inspect
from typing import Callable, cast, Generic, get_type_hints, Optional, overload, Type, TypeVar, Union

from ._provider import InterfaceProvider, Query
from .predicate import Predicate, PredicateConstraint
from .qualifier import QualifiedBy
from ..._internal.utils import FinalImmutable
from ..._internal.utils.meta import Singleton
from ...core import Dependency, inject

Itf = TypeVar('Itf', bound=type)
Impl = TypeVar('Impl', bound=Itf)
C = TypeVar('C', bound=type)
T = TypeVar('T')


class Interface(Singleton):
    @overload
    def __call__(self, klass: C) -> C:
        ...  # pragma: no cover

    @overload
    def __call__(self) -> Callable[[C], C]:
        ...  # pragma: no cover

    def __call__(self, klass: Optional[C] = None) -> Union[C, Callable[[C], C]]:
        @inject
        def register(cls: C, provider: InterfaceProvider = inject.me()) -> C:
            if not (isinstance(cls, type) and inspect.isclass(cls)):
                raise TypeError(f"Expected a class, got a {type(cls)!r}")

            provider.register(cls)

            return cast(C, cls)

        return klass and register(klass) or register

    def __getitem__(self, klass: Type[T]) -> InterfaceQueryBuilder[T]:
        return InterfaceQueryBuilder(klass)


class ImplementsWithPredicates(Generic[Itf]):
    def __init__(self, __interface: Itf, predicates: list[Predicate]) -> None:
        self._interface = __interface
        self.__predicates = predicates

    @inject
    def __call__(self, klass: C, __provider: InterfaceProvider = inject.me()) -> C:
        if not (isinstance(klass, type) and inspect.isclass(klass)):
            raise TypeError(f"Expected a class, got a {type(klass)!r}")

        __provider.register_implementation(self._interface, klass, self.__predicates)

        return cast(C, klass)


class implements(ImplementsWithPredicates[Itf]):
    def __init__(self, __interface: Itf) -> None:
        super().__init__(__interface, list())

    def when(self, *predicates: Predicate) -> ImplementsWithPredicates[Itf]:
        return ImplementsWithPredicates(self._interface, list(predicates))


def _generate_predicate_constraints(*args: PredicateConstraint,
                                    qualified_by: Optional[list[object]],
                                    qualified_by_one_of: Optional[list[object]],
                                    qualified_by_instance_of: Optional[type]
                                    ) -> list[tuple[type, Callable[..., bool]]]:
    filters: list[PredicateConstraint] = list(args)
    if not (qualified_by is None or isinstance(qualified_by, list)):
        raise TypeError(f"qualified_by should be None or a list, not {type(qualified_by)!r}")
    if qualified_by:
        filters.append(QualifiedBy(*qualified_by))

    if not (qualified_by_one_of is None or isinstance(qualified_by_one_of, list)):
        raise TypeError(f"qualified_by should be None or a list, not {type(qualified_by_one_of)!r}")
    if qualified_by_one_of:
        filters.append(QualifiedBy.one_of(qualified_by_one_of))

    if qualified_by_instance_of is not None:
        filters.append(QualifiedBy.instance_of(qualified_by_instance_of))

    result: list[tuple[type, Callable[..., bool]]] = list()
    for f in filters:
        predicate_type = get_type_hints(filter.__call__).get('predicate')
        if predicate_type is None:
            raise TypeError(f"Missing 'predicate' argument on the predicate filter {f}")
        if not isinstance(predicate_type, type) \
                or not issubclass(predicate_type, (Predicate, QualifiedBy)):
            raise TypeError(f"'predicate' argument type hint must be a predicate type.")
        result.append((predicate_type, f))

    return result


class InterfaceQueryBuilder(FinalImmutable, Generic[T]):
    __slots__ = ('klass',)
    klass: Type[T]

    def __init__(self, klass: Type[T]) -> None:
        if not (isinstance(klass, type) and inspect.isclass(klass)):
            raise TypeError(f"Expected a class, got a {type(klass)!r}")
        super().__init__(klass)

    def all(self,
            *constraints: PredicateConstraint,
            qualified_by: Optional[list[object]] = None,
            qualified_by_one_of: Optional[list[object]] = None,
            qualified_by_instance_of: Optional[type] = None
            ) -> Dependency[list[T]]:
        return Query.all(
            interface=self.klass,
            constraints=_generate_predicate_constraints(
                *constraints,
                qualified_by=qualified_by,
                qualified_by_one_of=qualified_by_one_of,
                qualified_by_instance_of=qualified_by_instance_of
            )
        )

    def single(self,
               *constraints: PredicateConstraint,
               qualified_by: Optional[list[object]] = None,
               qualified_by_one_of: Optional[list[object]] = None,
               qualified_by_instance_of: Optional[type] = None
               ) -> Dependency[T]:
        return Query.single(
            interface=self.klass,
            constraints=_generate_predicate_constraints(
                *constraints,
                qualified_by=qualified_by,
                qualified_by_one_of=qualified_by_one_of,
                qualified_by_instance_of=qualified_by_instance_of
            )
        )


interface = Interface()
