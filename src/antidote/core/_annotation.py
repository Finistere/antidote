from __future__ import annotations

import builtins
from dataclasses import dataclass

from typing_extensions import final, TypeGuard

from .._internal import API, Default, is_optional, optional_value, Singleton
from .data import Dependency, dependencyOf, ParameterDependency
from .exceptions import CannotInferDependencyError

__all__ = ["is_valid_class_type_hint", "InjectAnnotation"]

_BUILTINS_TYPES = {e for e in builtins.__dict__.values() if isinstance(e, type)}


@API.private
def is_valid_class_type_hint(type_hint: object) -> TypeGuard[type]:
    return (
        type_hint not in _BUILTINS_TYPES
        and isinstance(type_hint, type)
        and getattr(type_hint, "__module__", "") != "typing"
    )


@API.private
@final
@dataclass(frozen=True)
class InjectAnnotation(ParameterDependency, Singleton):
    __slots__ = ()

    def __antidote_parameter_dependency__(
        self, *, name: str, type_hint: object, type_hint_with_extras: object
    ) -> Dependency[object]:
        original_type_hint = type_hint
        default: object = Default.sentinel
        while is_optional(type_hint):
            type_hint = optional_value(type_hint)
            default = None

        if not is_valid_class_type_hint(type_hint):
            raise CannotInferDependencyError(
                f"Cannot use Inject with builtins, found: {original_type_hint!r}"
            )

        return dependencyOf[object](type_hint, default=default)
