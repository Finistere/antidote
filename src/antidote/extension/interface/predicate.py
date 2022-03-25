from __future__ import annotations, annotations

import bisect
from typing import Generic, Optional, TypeVar

from ..._internal.utils import FinalImmutable


class Predicate:
    def weight(self) -> Optional[PredicateWeight | tuple[int, ...] | int]:
        raise NotImplementedError()


P = TypeVar('P', bound=Predicate)


class PredicateConstraint(Generic[P]):
    def __call__(self, predicate: Optional[P]) -> bool:
        raise NotImplementedError()


class PredicateWeight(FinalImmutable):
    __slots__ = ('__priority_weights',)
    __priority_weights: list[tuple[int, int]]

    def __init__(self, weight: Optional[tuple[int, ...] | int] = None):
        if weight is None:
            pw: list[tuple[int, int]] = list()
        elif isinstance(weight, int):
            pw = [(0, weight)] if weight != 0 else []
        elif isinstance(weight, tuple) and all(isinstance(w, int) for w in weight):
            pw = [(len(weight) - i - 1, w) for i, w in enumerate(weight) if w != 0]
        else:
            raise TypeError(f"weight must be either None, an int or a tuple of weights, "
                            f"not a {type(weight)!r}")
        super().__init__(pw)

    def set(self, priority: int, weight: int) -> PredicateWeight:
        if not isinstance(priority, int):
            raise TypeError(f"priority must be an int, not a {type(priority)!r}")
        if not isinstance(weight, int):
            raise TypeError(f"priority must be an int, not a {type(weight)!r}")
        if weight == 0:
            try:
                del self[priority]
            except IndexError:
                pass
        else:
            self[priority] = weight
        return self

    def __setitem__(self, priority: int, weight: int) -> None:
        if not isinstance(priority, int):
            raise TypeError(f"priority must be an int, not a {type(priority)!r}")
        if not isinstance(weight, int):
            raise TypeError(f"priority must be an int, not a {type(weight)!r}")
        if weight != 0:
            pw = (priority, weight)
            i = bisect.bisect(self.__priority_weights, pw)
            if self.__priority_weights[i - 1][0] == priority:
                self.__priority_weights[i - 1] = pw
            else:
                self.__priority_weights.insert(i, pw)

    def __delitem__(self, priority: int) -> None:
        if not isinstance(priority, int):
            raise TypeError(f"priority must be an int, not a {type(priority)!r}")
        pw = (priority, 0)
        i = bisect.bisect(self.__priority_weights, pw)
        if self.__priority_weights[i - 1][0] == priority:
            del self.__priority_weights[i - 1]

    def __getitem__(self, priority: int) -> int:
        if not isinstance(priority, int):
            raise TypeError(f"priority must be an int, not a {type(priority)!r}")
        pw = (priority, 0)
        i = bisect.bisect(self.__priority_weights, pw)
        if self.__priority_weights[i - 1][0] == priority:
            return self.__priority_weights[i - 1][1]
        raise IndexError(priority)

    def __add__(self, other: PredicateWeight) -> PredicateWeight:
        result = PredicateWeight()
        append = result.__priority_weights.append
        left = 0
        right = 0
        while left < len(self.__priority_weights) and right < len(other.__priority_weights):
            (l_priority, l_weight) = self.__priority_weights[left]
            (r_priority, r_weight) = other.__priority_weights[right]
            if l_priority < r_priority:
                append((l_priority, l_weight))
                left += 1
            elif r_priority < l_priority:
                append((r_priority, r_weight))
                right += 1
            else:
                append((l_priority, l_weight + r_weight))
                left += 1
                right += 1

        while left < len(self.__priority_weights):
            append(self.__priority_weights[left])
            left += 1

        while right < len(other.__priority_weights):
            append(other.__priority_weights[right])
            right += 1

        return result

    def __neg__(self) -> PredicateWeight:
        result = PredicateWeight()
        for (priority, weight) in self.__priority_weights:
            result.__priority_weights.append((priority, -weight))
        return result

    def __sub__(self, other: PredicateWeight) -> PredicateWeight:
        return self + (-other)

    def __lt__(self, other: PredicateWeight) -> bool:
        left = len(self.__priority_weights) - 1
        right = len(other.__priority_weights) - 1
        while left >= 0 and right >= 0:
            ll = self.__priority_weights[left]
            rr = other.__priority_weights[right]
            if ll == rr:
                left -= 1
                right -= 1
            else:
                return ll < rr

        if left >= 0:
            return self.__priority_weights[left][1] < 0

        if right >= 0:
            return other.__priority_weights[right][1] > 0

        return False

    def __le__(self, other: PredicateWeight) -> bool:
        return self < other or self == other

    def __eq__(self, other: PredicateWeight) -> bool:
        if len(self.__priority_weights) != len(other.__priority_weights):
            return False

        for left, right in zip(self.__priority_weights, other.__priority_weights):
            if left != right:
                return False

        return True

    def __ne__(self, other: PredicateWeight) -> bool:
        return not (self == other)

    def __gt__(self, other: PredicateWeight) -> bool:
        return not (other <= self)

    def __ge__(self, other: PredicateWeight) -> bool:
        return not (other < self)
