from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Optional

from typing_extensions import final

from ..._internal import API
from .predicate import NeutralWeight, PredicateConstraint

__all__ = ["QualifiedBy"]


@API.private  # use QualifiedBy.nothing
def not_qualified(predicate: Optional[QualifiedBy]) -> bool:
    return predicate is None


@API.public
@final
@dataclass(frozen=True, eq=True)
class QualifiedBy:
    """
    Qualifiers for :py:func:`.interface` / :py:class:`.implements`. Implementations can be
    qualified with one or multiple objects. One can then impose some constraints on those qualifiers
    to retrieve only a selection of implementations.

    Qualifiers are identified by their :py:func:`id` and not their equality. Moreover builtins
    types, such as :py:class:`int` or :py:class:`str`, cannot be used. This ensures that usage of
    a specific qualifiers is easy to track.

    .. doctest:: lib_interface_qualifiers_qualified_by

        >>> from antidote import QualifiedBy, interface, implements, world, inject, instanceOf
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
        >>> world[instanceOf(Alert).single(qualified_by=V1)]
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
        >>> world[instanceOf(Alert).single(qualified_by=V1)]
        <AlertV1 object at ...>

    Multiple constraints can be used to query the exact implementation one needs,
    :code:`qualified_by` enforces that the specified qualifiers are present:

    .. doctest:: lib_interface_qualifiers_qualified_by

        >>> world[instanceOf(Alert).single(qualified_by=[V2, V3])]
        <AlertV2andV3 object at ...>
        >>> world[instanceOf(Alert).all(qualified_by=V3)]
        [<AlertV3 object at ...>, <AlertV2andV3 object at ...>]

    One can also require that at least one qualifier of a list must be present with
    :py:meth:`.QualifiedBy.one_of` or :code:`qualified_by_one_of`.

    All of those constraints can be used together or multiple times without any issues.
    """

    nothing: ClassVar[PredicateConstraint[QualifiedBy]] = not_qualified

    __slots__ = ("qualifiers",)
    qualifiers: frozenset[object]

    @classmethod
    def one_of(cls, *qualifiers: object) -> PredicateConstraint[QualifiedBy]:
        """
        Constraints enforcing the presence of a least one qualifier on a implementation.

        .. doctest:: lib_interface_qualifiers_one_of

            >>> from antidote import QualifiedBy, interface, implements, world, instanceOf
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
            >>> world[instanceOf(Alert).all(qualified_by_one_of=[V1, V2])]
            [<AlertV2 object at ...>, <AlertV1 object at ...>]
            >>> world[instanceOf(Alert).all(QualifiedBy.one_of(V1, V2))]
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

        object.__setattr__(self, "qualifiers", frozenset(qualifiers))

    def __call__(self, predicate: Optional[QualifiedBy]) -> bool:
        if predicate is None:
            return False

        return self.qualifiers.issubset(predicate.qualifiers)

    @staticmethod
    def weight() -> NeutralWeight:
        return NeutralWeight()

    def __antidote_debug_repr__(self) -> str:
        return f"qualified_by=[{', '.join(map(repr, self.qualifiers))}]"


@API.private  # Use QualifiedBy.one_of
@final
@dataclass(frozen=True, eq=True)
class QualifiedByOneOf:
    __slots__ = ("__qualified_by",)
    __qualified_by: QualifiedBy

    def __call__(self, predicate: Optional[QualifiedBy]) -> bool:
        if predicate is None:
            return False

        return not self.__qualified_by.qualifiers.isdisjoint(predicate.qualifiers)

    def __antidote_debug_repr__(self) -> str:
        return f"qualified_by_one_of=[{', '.join(map(repr, self.__qualified_by.qualifiers))}]"
