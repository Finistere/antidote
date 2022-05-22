from __future__ import annotations

import functools
import inspect
from dataclasses import make_dataclass
from typing import Any, Callable, cast, Optional, overload, Type, TypeVar

from typing_extensions import final, ParamSpec, Protocol, runtime_checkable

from ...core import inject
from ..._internal import API
from ..._internal.utils.meta import Singleton

__all__ = [
    "NeutralWeight",
    "Predicate",
    "PredicateWeight",
    "PredicateConstraint",
    "MergeablePredicateConstraint",
    "MergeablePredicate",
    "predicate",
]

from ...core.exceptions import DoubleInjectionError

SelfWeight = TypeVar("SelfWeight", bound="PredicateWeight")
T = TypeVar("T")
P = ParamSpec("P")


@API.experimental
class PredicateWeight(Protocol):
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
        >>> from antidote.lib.interface import Predicate, QualifiedBy
        >>> class Weight:
        ...     def __init__(self, value: int) -> None:
        ...         self.value = value
        ...
        ...     @classmethod
        ...     def of_neutral(cls, predicate: Optional[Predicate[Any]]) -> 'Weight':
        ...         if isinstance(predicate, QualifiedBy):
        ...             return Weight(len(predicate.qualifiers))
        ...         return Weight(0)
        ...
        ...     def __lt__(self, other: 'Weight') -> bool:
        ...         return self.value < other.value
        ...
        ...     def __add__(self, other: 'Weight') -> 'Weight':
        ...         return Weight(self.value + other.value)
    """

    @classmethod
    def of_neutral(cls: Type[SelfWeight], predicate: Optional[Predicate[Any]]) -> SelfWeight:
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


@API.experimental
@final
class NeutralWeight(Singleton):
    """
    Simple :py:class:`.PredicateWeight` implementation where the weight
    always stays the same, neutral. All implementations are treated equally.
    """

    @classmethod
    def of_neutral(cls, predicate: Optional[Predicate[Any]]) -> NeutralWeight:
        return cls()

    def __lt__(self, other: NeutralWeight) -> bool:
        return False

    def __add__(self, other: NeutralWeight) -> NeutralWeight:
        return self

    def __str__(self) -> str:
        return "N"

    def __repr__(self) -> str:
        return "NeutralWeight"


WeightCo = TypeVar("WeightCo", bound=PredicateWeight, covariant=True)


@API.experimental
@runtime_checkable
class Predicate(Protocol[WeightCo]):
    """
    A predicate can be used to define in which conditions an implementations should be used. A
    single method must be implemented :code:`weight()` which should return an optional
    :py:class:`.PredicateWeight`. It is called immediately at import time.
    The weight is used to determine the ordering of the implementations. If :py:obj:`None` is
    returned, the implementation will not be used at all, which allows one to customize which
    implementations are available at import time.

    Antidote only provides a single weight system out of the box, :py:class:`.NeutralWeight`
    which as its name implies does not provide any ordering. All implementations are treated
    equally. You're free to use your own weight though, see :py:class:`.PredicateWeight`
    for more details.

    .. doctest:: lib_interface_predicate

        >>> from typing import Optional
        >>> import os
        >>> from antidote import Constants, const, inject, interface, implements, world
        >>> from antidote.lib.interface import NeutralWeight
        >>> class Conf(Constants):
        ...     CLOUD = const[str]('aws')
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
        >>> world.get[ObjectStorage].all()
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
        RuntimeError: Cannot have multiple predicates ...

    To provide some flexibility :py:class:`.Predicate` can be merged if they implement
    :py:class:`.MergeablePredicate`.
    """

    def weight(self) -> Optional[WeightCo]:
        ...


SelfP = TypeVar("SelfP", bound=Predicate[Any])


@API.experimental
@runtime_checkable
class MergeablePredicate(Predicate[WeightCo], Protocol):
    """
    A :py:class:`.Predicate` implementing :code:`merge` can be specified multiple times. All
    instances will be merged at import time, ensuring only one instance exists for a given
    implementation.

    .. doctest:: lib_interface_mergeable_predicate

        >>> from typing import Optional
        >>> from antidote.lib.interface import NeutralWeight
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
    def merge(cls: Type[SelfP], a: SelfP, b: SelfP) -> SelfP:
        ...


Pct = TypeVar("Pct", bound=Predicate[Any], contravariant=True)


@API.experimental
@runtime_checkable
class PredicateConstraint(Protocol[Pct]):
    """
    A constraint can be used to define at runtime whether a given predicate matches a specific
    criteria or not. Antidote will evaluate the constraint on all predicate that matches the
    argument type hint. If not predicate of this type is present on an implementation, it is
    evaluated with :py:obj:`None` instead.

    .. doctest:: lib_interface_constraint

        >>> from typing import Optional, Protocol
        >>> from antidote import QualifiedBy, interface, implements, world
        >>> class NotQualified:
        ...     def evaluate(self, predicate: Optional[QualifiedBy]) -> bool:
        ...         return predicate is None
        >>> class AtLeastTwoQualifiers:
        ...     def evaluate(self, predicate: Optional[QualifiedBy]) -> bool:
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
        >>> world.get[Dummy].single(NotQualified())
        <NoQualifiers ...>
        >>> world.get[Dummy].single(AtLeastTwoQualifiers())
        <TwoQualifiers ...>

    Contrary to :py:class:`.Predicate` you can use multiple instances of a single
    constraint class. But, you can still implement :py:class:`.MergeablePredicateConstraint` which
    allows for runtime optimization by merging them.

    """

    def evaluate(self, predicate: Optional[Pct]) -> bool:
        ...


SelfPC = TypeVar("SelfPC", bound=PredicateConstraint[Any])


@API.experimental
@runtime_checkable
class MergeablePredicateConstraint(PredicateConstraint[Pct], Protocol):
    """
    A :py:class:`.PredicateConstraint` implementing :code:`merge` allows for runtime optimization by
    merging all constraints into one.

    .. doctest:: lib_interface_mergeable_predicate_constraint

        >>> from typing import Optional
        >>> from antidote.lib.interface import NeutralWeight, QualifiedBy
        >>> class NotQualified:
        ...     @classmethod
        ...     def merge(cls, a: 'NotQualified', b: 'NotQualified') -> 'NotQualified':
        ...         return a
        ...
        ...     def evaluate(self, predicate: Optional[QualifiedBy]) -> bool:
        ...         return predicate is None

    """

    @classmethod
    def merge(cls: Type[SelfPC], a: SelfPC, b: SelfPC) -> SelfPC:
        ...


@overload
def predicate(__func: Callable[P, bool]) -> Callable[P, Predicate[NeutralWeight]]:
    ...


@overload
def predicate(__func: Callable[P, Optional[WeightCo]]) -> Callable[P, Predicate[WeightCo]]:
    ...


@API.experimental
def predicate(
    __func: Callable[P, bool] | Callable[P, Optional[WeightCo]]
) -> Callable[P, Predicate[NeutralWeight]] | Callable[P, Predicate[WeightCo]]:
    """
    Create a new predicate based on the decorated function.

    .. doctest:: lib_interface_predicate_decorator

        >>> from antidote import world
        >>> from antidote.lib.interface import predicate
        >>> @predicate
        ... def use_me(condition: bool) -> bool:
        ...     return condition
        >>> from antidote import interface, implements
        >>> @interface
        ... class Base:
        ...     pass
        >>> @implements(Base).when(use_me(True))
        ... class BaseImpl(Base):
        ...     pass
        >>> world.get(Base)
        <BaseImpl ...>


    Args:
        __func: **/positional-only/** Function to call defining whether the implementation can
            be used or not. The function should either return a boolean or an optional weight.
            The function will be injected if not already.

    Returns:
        A new function with the same arguments returning a predicate with a constant weight.
    """
    if not inspect.isfunction(__func):
        raise TypeError(f"@predicate can only decorate functions, not a {type(__func)!r}")

    try:
        __func = inject(__func)
    except DoubleInjectionError:
        pass

    camel_case_name = "".join(part.title() for part in __func.__name__.split("_"))
    cls = make_dataclass(
        f"{camel_case_name}Predicate",
        [("_weight", object)],
        namespace={"weight": lambda self: self._weight},  # type: ignore
        frozen=True,
    )
    predicate_cls = cast(Callable[[object], Predicate[Any]], cls)

    @functools.wraps(__func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> Predicate[Any]:
        result = __func(*args, **kwargs)
        if isinstance(result, bool):
            return predicate_cls(NeutralWeight() if result else None)
        return predicate_cls(result)

    return wrapped
