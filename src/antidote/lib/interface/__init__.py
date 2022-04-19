from .interface import ImplementationsOf, implements, interface
from .predicate import NeutralWeight, Predicate, predicate, PredicateConstraint, PredicateWeight
from .qualifier import QualifiedBy

from ..._internal import API

__all__ = [
    'interface',
    'implements',
    'ImplementationsOf',
    'register_interface_provider',
    'QualifiedBy',
    'predicate',
    'Predicate',
    'PredicateConstraint',
    'PredicateWeight',
    'NeutralWeight',
]


@API.experimental
def register_interface_provider() -> None:
    from ... import world
    from ._provider import InterfaceProvider
    world.provider(InterfaceProvider)
