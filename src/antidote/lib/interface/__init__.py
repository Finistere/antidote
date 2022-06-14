from __future__ import annotations

from ..._internal import API
from ...core import Catalog
from ._interface import InterfaceImpl, OverridableImpl
from .interface import implements, instanceOf, Interface, is_interface, Overridable
from .predicate import NeutralWeight, Predicate, PredicateConstraint, PredicateWeight
from .qualifier import QualifiedBy

__all__ = [
    "interface",
    "is_interface",
    "implements",
    "overridable",
    "instanceOf",
    "antidote_interface",
    "QualifiedBy",
    "Predicate",
    "PredicateConstraint",
    "PredicateWeight",
    "NeutralWeight",
]


interface: Interface = InterfaceImpl()
overridable: Overridable = OverridableImpl()


@API.public
def antidote_interface(catalog: Catalog) -> None:
    from ..injectable import antidote_injectable
    from ..lazy import antidote_lazy
    from ._provider import InterfaceProvider

    if InterfaceProvider not in catalog.providers:
        catalog.include(InterfaceProvider)
    catalog.include(antidote_injectable)
    catalog.include(antidote_lazy)
