from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import cast, Optional, Tuple

from typing_extensions import final

from .predicate import NeutralWeight, PredicateConstraint
from ..._internal import API

__all__ = ["QualifiedBy"]

_BUILTIN_TYPES = cast(
    Tuple[type, ...], (int, float, str, list, dict, set, tuple, bytes, bytearray, bool, complex)
)


@API.public
@final
@dataclass(frozen=True, init=False)
class QualifiedBy:
    """
    Qualifiers for :py:func:`.interface` / :py:class:`.implements`. Implementations can be
    qualified with one or multiple objects. One can then impose some constraints on those qualifiers
    to retrieve only a selection of implementations.

    Qualifiers are identified by their :py:func:`id` and not their equality. Moreover builtins
    types, such as :py:class:`int` or :py:class:`str`, cannot be used. This ensures that usage of
    a specific qualifiers is easy to track.

    .. doctest:: lib_interface_qualifiers_qualified_by

        >>> from antidote import QualifiedBy, interface, implements, world, inject
        >>> V1, V2, V3 = object(), object(), object()
        >>> @interface
        ... class Alert:
        ...     pass
        >>> @implements(Alert).when(qualified_by=V1)
        ... class AlertV1(Alert):
        ...     pass
        >>> @implements(Alert).when(qualified_by=[V2, V3])
        ... class AlertV2andV3(Alert):
        ...     pass
        >>> world.get[Alert].single(qualified_by=V1)
        <AlertV1 object at ...>
        >>> @inject
        ... def v1alert(alert: Alert = inject.me(qualified_by=V1)) -> Alert:
        ...     return alert
        >>> v1alert()
        <AlertV1 object at ...>

    :py:class:`.QualifiedBy` can also be used directly:

    .. doctest:: lib_interface_qualifiers_qualified_by

        >>> @implements(Alert).when(QualifiedBy(V3))
        ... class AlertV3(Alert):
        ...     pass
        >>> world.get[Alert].single(QualifiedBy(V1))
        <AlertV1 object at ...>

    Multiple constraints can be used to query the exact implementation one needs,
    :code:`qualified_by` enforces that the specified qualifiers are present:

    .. doctest:: lib_interface_qualifiers_qualified_by

        >>> world.get[Alert].single(qualified_by=[V2, V3])
        <AlertV2andV3 object at ...>
        >>> world.get[Alert].all(qualified_by=V3)
        [<AlertV3 object at ...>, <AlertV2andV3 object at ...>]

    One can also require that at least one qualifier of a list must be present with
    :py:meth:`.QualifiedBy.one_of` or :code:`qualified_by_one_of`.

    All of those constraints can be used together or multiple times without any issues.
    """

    __slots__ = ("qualifiers",)
    qualifiers: list[object]

    @classmethod
    def one_of(cls, *qualifiers: object) -> PredicateConstraint[QualifiedBy]:
        """
        Constraints enforcing the presence of a least one qualifier on a implementation.

        .. doctest:: lib_interface_qualifiers_one_of

            >>> from antidote import QualifiedBy, interface, implements, world
            >>> V1, V2 = object(), object()
            >>> @interface
            ... class Alert:
            ...     pass
            >>> @implements(Alert).when(qualified_by=V1)
            ... class AlertV1(Alert):
            ...     pass
            >>> @implements(Alert).when(qualified_by=V2)
            ... class AlertV2(Alert):
            ...     pass
            >>> world.get[Alert].all(qualified_by_one_of=[V1, V2])
            [<AlertV2 object at ...>, <AlertV1 object at ...>]
            >>> world.get[Alert].all(QualifiedBy.one_of(V1, V2))
            [<AlertV2 object at ...>, <AlertV1 object at ...>]

        Args:
            *qualifiers: All potential qualifiers.
        """
        return QualifiedByOneOf(QualifiedBy(*qualifiers))

    @classmethod
    def merge(cls, a: QualifiedBy, b: QualifiedBy) -> QualifiedBy:
        return QualifiedBy(*a.qualifiers, *b.qualifiers)

    def __init__(self, *qualifiers: object):
        """
        Args:
            *qualifiers: Qualifiers to use for an implementation.
        """
        if len(qualifiers) == 0:
            raise ValueError("At least one qualifier must be given.")

        for qualifier in qualifiers:
            if qualifier is None or isinstance(qualifier, _BUILTIN_TYPES):
                raise TypeError(
                    f"Invalid qualifier: {qualifier!r}. "
                    f"It cannot be None or an instance of a builtin type"
                )

        object.__setattr__(
            self,
            "qualifiers",
            [next(group) for _, group in itertools.groupby(sorted(qualifiers, key=id), key=id)],
        )

    def evaluate(self, predicate: Optional[QualifiedBy]) -> bool:
        if predicate is None:
            return False

        if len(self.qualifiers) > len(predicate.qualifiers):
            return False

        i = 0
        j = 0
        while i < len(self.qualifiers) and j < len(predicate.qualifiers):
            if self.qualifiers[i] is predicate.qualifiers[j]:
                i += 1
                j += 1
            else:
                j += 1

        return i == len(self.qualifiers)

    @staticmethod
    def weight() -> NeutralWeight:
        return NeutralWeight()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, QualifiedBy):
            return False

        if len(self.qualifiers) != len(other.qualifiers):
            return False

        for a, b in zip(self.qualifiers, other.qualifiers):
            if a is not b:
                return False

        return True

    def __hash__(self) -> int:
        return hash(tuple(id(q) for q in self.qualifiers))


@API.private  # Use QualifiedBy.one_of
@final
@dataclass(frozen=True, eq=True, unsafe_hash=True)
class QualifiedByOneOf:
    __slots__ = ("__qualified_by",)
    __qualified_by: QualifiedBy

    def evaluate(self, predicate: Optional[QualifiedBy]) -> bool:
        if predicate is None:
            return False

        i = 0
        j = 0
        while i < len(self.__qualified_by.qualifiers) and j < len(predicate.qualifiers):
            idi = id(self.__qualified_by.qualifiers[i])
            idj = id(predicate.qualifiers[j])
            if idi == idj:
                return True
            if idi < idj:
                i += 1
            else:
                j += 1

        return False
