from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Type, TypeVar

from typing_extensions import final, Protocol, runtime_checkable

from ..._internal import API, Singleton

__all__ = [
    "NeutralWeight",
    "Predicate",
    "ImplementationWeight",
    "PredicateConstraint",
    "MergeablePredicateConstraint",
    "MergeablePredicate",
    "HeterogeneousWeightError",
]

from ...core import AntidoteError

SelfWeight = TypeVar("SelfWeight", bound="ImplementationWeight")
OutWeight = TypeVar("OutWeight", bound="ImplementationWeight", covariant=True)


@API.public
@runtime_checkable
class ImplementationWeight(Protocol):
    """
    The weight defines the ordering of the implementations. When requesting all implementations,
    their ordering is the one defined by their weight. For a single implementation, it's the one
    with the highest weight. If multiple implementations have the highest weight, an exception will
    be raised when requesting a single implementation.

    A weight must define the operator :code:`<` for the ordering, :code:`+` to sum the weights of
    multiple predicates and the method :code:`of_neutral` to handle predicates with a neutral
    :py:class:`.NeutralWeight`.

    Mixing predicates and/or implementations with :py:class:`.NeutralWeight` and your
    custom weight is supported as long as your method :code:`of_neutral` can provide a weight.
    However, multiple custom weights are not.

    All methods are only called at import time, when declaring dependencies.

    .. doctest:: lib_interface_weight

        >>> from typing import Optional, Any
        >>> from antidote import Predicate, QualifiedBy
        >>> class Weight:
        ...     def __init__(self, value: int) -> None:
        ...         self.__value = value
        ...
        ...     @classmethod
        ...     def of_neutral(cls, predicate: Optional[Predicate[Any]]) -> 'Weight':
        ...         if isinstance(predicate, QualifiedBy):
        ...             return Weight(len(predicate.qualifiers))
        ...         return Weight(0)
        ...
        ...     def __lt__(self, other: 'Weight') -> bool:
        ...         return self.__value < other.__value
        ...
        ...     def __add__(self, other: 'Weight') -> 'Weight':
        ...         return Weight(self.__value + other.__value)
    """

    @classmethod
    def neutral(cls: Type[SelfWeight]) -> SelfWeight:
        ...

    @classmethod
    def of_neutral_predicate(cls: Type[SelfWeight], predicate: Predicate[Any]) -> SelfWeight:
        """
        Called when a predicate has a :py:class:`.NeutralWeight` or when an
        implementation has no weight at all. In which case :py:obj:`None` is given as argument.

        Args:
            predicate: Neutral weighted predicate or None for an implementation without predicates.

        Returns:
            Weight of the predicate or implementation.
        """
        ...

    def __lt__(self: SelfWeight, other: SelfWeight) -> bool:
        """
        Less than operator, used for the sorting of weights.

        Args:
            other: other will always be an instance of the current weight class.

        """
        ...

    def __add__(self: SelfWeight, other: SelfWeight) -> SelfWeight:
        """
        Plus operator, used to sum weights of predicates.

        Args:
            other: other will always be an instance of the current weight class.

        """
        ...


@API.public
@final
@dataclass(frozen=True)
class NeutralWeight(Singleton):
    """
    Simple :py:class:`.ImplementationWeight` implementation where the weight
    always stays the same, neutral. All implementations are treated equally.
    """

    __slots__ = ()

    @classmethod
    def neutral(cls) -> NeutralWeight:
        return NeutralWeight()

    @classmethod
    def of_neutral_predicate(cls, predicate: Predicate[Any]) -> NeutralWeight:
        return cls.neutral()

    def __lt__(self, other: NeutralWeight) -> bool:
        return False

    def __add__(self, other: NeutralWeight) -> NeutralWeight:
        return self

    def __repr__(self) -> str:
        return type(self).__name__


@API.public
@runtime_checkable
class Predicate(Protocol[OutWeight]):
    """
    A predicate can be used to define in which conditions an implementations should be used. A
    single method must be implemented :code:`weight()` which should return an optional
    :py:class:`.ImplementationWeight`. It is called immediately at import time.
    The weight is used to determine the ordering of the implementations. If :py:obj:`None` is
    returned, the implementation will not be used at all, which allows one to customize which
    implementations are available at import time.

    Antidote only provides a single weight system out of the box, :py:class:`.NeutralWeight`
    which as its name implies does not provide any ordering. All implementations are treated
    equally. You're free to use your own weight though, see :py:class:`.ImplementationWeight`
    for more details.

    .. doctest:: lib_interface_predicate

        >>> from typing import Optional
        >>> import os
        >>> from antidote import const, inject, interface, implements, world, NeutralWeight, instanceOf
        >>> class Conf:
        ...     CLOUD = const('aws')
        >>> class InCloud:
        ...     def __init__(self, cloud: str) -> None:
        ...         self.cloud = cloud
        ...
        ...     @inject
        ...     def weight(self, cloud: str = Conf.CLOUD) -> Optional[NeutralWeight]:
        ...         if cloud == self.cloud:
        ...             return NeutralWeight()
        >>> @interface
        ... class ObjectStorage:
        ...     def put(self, name: str, data: bytes) -> None:
        ...         pass
        >>> @implements(ObjectStorage).when(InCloud('aws'))
        ... class AwsStorage(ObjectStorage):
        ...     pass
        >>> @implements(ObjectStorage).when(InCloud('gcp'))
        ... class GCPStorage(ObjectStorage):
        ...     pass
        >>> world[instanceOf(ObjectStorage).all()]
        [<AwsStorage ...>]

    .. tip::

        Consider using :py:func:`.predicate` for simple predicates.

    Predicates can share mother classes, but only one predicate of a specific type can be applied
    on a implementation:

    .. doctest:: lib_interface_predicate

        >>> @implements(ObjectStorage).when(InCloud('gcp'), InCloud('gcp'))
        ... class GCPStorage(ObjectStorage):
        ...     pass
        Traceback (most recent call last):
          File "<stdin>", line 1, in ?
        TypeError: Cannot have multiple predicates ...

    To provide some flexibility :py:class:`.Predicate` can be merged if they implement
    :py:class:`.MergeablePredicate`.
    """

    def weight(self) -> Optional[OutWeight]:
        ...


SelfPredicate = TypeVar("SelfPredicate", bound=Predicate[Any])


@API.public
@runtime_checkable
class MergeablePredicate(Predicate[OutWeight], Protocol):
    """
    A :py:class:`.Predicate` implementing :code:`merge` can be specified multiple times. All
    instances will be merged at import time, ensuring only one instance exists for a given
    implementation.

    .. doctest:: lib_interface_mergeable_predicate

        >>> from typing import Optional
        >>> from antidote import NeutralWeight
        >>> class UseMe:
        ...     @classmethod
        ...     def merge(cls, a: 'UseMe', b: 'UseMe') -> 'UseMe':
        ...         return UseMe(a.condition and b.condition)
        ...
        ...     def __init__(self, condition: bool) -> None:
        ...         self.condition = condition
        ...
        ...     def weight(self) -> Optional[NeutralWeight]:
        ...         return NeutralWeight() if self.condition else None


    """

    @classmethod
    def merge(cls: Type[SelfPredicate], a: SelfPredicate, b: SelfPredicate) -> SelfPredicate:
        ...


InPredicate = TypeVar("InPredicate", bound=Predicate[Any], contravariant=True)


@API.public
@runtime_checkable
class PredicateConstraint(Protocol[InPredicate]):
    """
    A constraint can be used to define at runtime whether a given predicate matches a specific
    criteria or not. Antidote will evaluate the constraint on all predicate that matches the
    argument type hint. If not predicate of this type is present on an implementation, it is
    evaluated with :py:obj:`None` instead.

    .. doctest:: lib_interface_constraint

        >>> from typing import Optional, Protocol
        >>> from antidote import QualifiedBy, interface, implements, world, instanceOf
        >>> # Equivalent to QualifiedBy.nothing
        ... def not_qualified(predicate: Optional[QualifiedBy]) -> bool:
        ...         return predicate is None
        >>> def at_least_two_qualifiers(predicate: Optional[QualifiedBy]) -> bool:
        ...         return predicate is not None and len(predicate.qualifiers) >= 2
        >>> @interface
        ... class Dummy(Protocol):
        ...     pass
        >>> @implements(Dummy)
        ... class NoQualifiers:
        ...     pass
        >>> @implements(Dummy).when(qualified_by=object())
        ... class OneQualifier:
        ...     pass
        >>> @implements(Dummy).when(qualified_by=[object(), object()])
        ... class TwoQualifiers:
        ...     pass
        >>> world[instanceOf(Dummy).single(not_qualified)]
        <NoQualifiers ...>
        >>> world[instanceOf(Dummy).single(at_least_two_qualifiers)]
        <TwoQualifiers ...>

    Contrary to :py:class:`.Predicate` you can use multiple instances of a single
    constraint class. But, you can still implement :py:class:`.MergeablePredicateConstraint` which
    allows for runtime optimization by merging them.

    """

    def __call__(self, predicate: Optional[InPredicate]) -> bool:
        ...


SelfPredicateConstraint = TypeVar("SelfPredicateConstraint", bound=PredicateConstraint[Any])


@API.public
@runtime_checkable
class MergeablePredicateConstraint(PredicateConstraint[InPredicate], Protocol):
    """
    A :py:class:`.PredicateConstraint` implementing :code:`merge` allows for runtime optimization by
    merging all constraints into one.

    .. doctest:: lib_interface_mergeable_predicate_constraint

        >>> from typing import Optional
        >>> from antidote import NeutralWeight, QualifiedBy
        >>> class NotQualified:
        ...     @classmethod
        ...     def merge(cls, a: 'NotQualified', b: 'NotQualified') -> 'NotQualified':
        ...         return a
        ...
        ...     def evaluate(self, predicate: Optional[QualifiedBy]) -> bool:
        ...         return predicate is None

    """

    @classmethod
    def merge(
        cls: Type[SelfPredicateConstraint], a: SelfPredicateConstraint, b: SelfPredicateConstraint
    ) -> SelfPredicateConstraint:
        ...


@API.public
class HeterogeneousWeightError(AntidoteError):
    @API.private
    def __init__(self, a: ImplementationWeight, b: ImplementationWeight) -> None:
        super().__init__(f"Heterogeneous weight types found: {type(a)!r} and {type(b)!r}")
