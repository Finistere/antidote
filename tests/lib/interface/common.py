from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TypeVar

from antidote import NeutralWeight, Predicate, QualifiedBy

T = TypeVar("T")


def _(x: T) -> T:
    return x


@dataclass(frozen=True)
class Weight:
    value: float

    def __init__(self, value: float | Weight) -> None:
        object.__setattr__(self, "value", value.value if isinstance(value, Weight) else value)

    @classmethod
    def neutral(cls) -> Weight:
        return Weight(0)

    @classmethod
    def of_neutral_predicate(cls, predicate: Predicate[Any]) -> Weight:
        if isinstance(predicate, QualifiedBy):
            return Weight(len(predicate.qualifiers))
        if isinstance(predicate, OnlyIf):
            return Weight(10)
        return Weight(1)

    def __lt__(self, other: Weight) -> bool:
        return self.value < other.value

    def __add__(self, other: Weight) -> Weight:
        return Weight(self.value + other.value)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.value}"


def only_if(condition: bool) -> bool:
    return condition


def weighted(value: Optional[Weight | float] = None) -> Optional[Weight]:
    return Weight(value) if value is not None else None


@dataclass
class OnlyIf:
    condition: bool
    kwargs: dict[str, object]

    def __init__(self, __condition: bool, **kwargs: object) -> None:
        self.condition = __condition
        self.kwargs = kwargs

    def weight(self) -> NeutralWeight | None:
        return NeutralWeight() if self.condition else None


@dataclass
class OnlyIf2:
    condition: bool

    def weight(self) -> NeutralWeight | None:
        return NeutralWeight() if self.condition else None


@dataclass
class Weighted:
    _weight: Weight | float | None
    kwargs: dict[str, object]

    def __init__(self, __weight: Weight | float | None, **kwargs: object) -> None:
        self._weight = __weight
        self.kwargs = kwargs

    def weight(self) -> Weight | None:
        return Weight(self._weight) if self._weight is not None else None

    @classmethod
    def merge(cls, a: Weighted, b: Weighted) -> Weighted:
        wa = a.weight()
        wb = b.weight()
        return Weighted(None) if wa is None or wb is None else Weighted(wa + wb)


@dataclass
class Weighted2:
    _weight: Weight | float | None

    def weight(self) -> Weight | None:
        return Weight(self._weight) if self._weight is not None else None


@dataclass(frozen=True)
class WeightAlt:
    value: float

    def __init__(self, value: float | WeightAlt) -> None:
        object.__setattr__(self, "value", value.value if isinstance(value, WeightAlt) else value)

    @classmethod
    def neutral(cls) -> WeightAlt:
        raise NotImplementedError()

    @classmethod
    def of_neutral_predicate(cls, predicate: Predicate[Any]) -> WeightAlt:
        raise NotImplementedError()

    def __lt__(self, other: WeightAlt) -> bool:
        raise NotImplementedError()

    def __add__(self, other: WeightAlt) -> WeightAlt:
        raise NotImplementedError()

    def __str__(self) -> str:
        raise NotImplementedError()


def weighted_alt(value: Optional[WeightAlt | float] = None) -> Optional[WeightAlt]:
    return WeightAlt(value) if value is not None else None


@dataclass
class WeightedAlt:
    _weight: WeightAlt | float | None

    def weight(self) -> WeightAlt | None:
        return WeightAlt(self._weight) if self._weight is not None else None
