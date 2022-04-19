from __future__ import annotations

from typing import Callable, cast, Mapping, Optional, TypeVar

from ._provider import InjectableProvider
from ..._internal import API
from ...core import inject, Scope, Wiring
from ...core.exceptions import DuplicateDependencyError

C = TypeVar('C', bound=type)


@API.private
@inject
def register_injectable(*,
                        klass: type,
                        scope: Optional[Scope],
                        wiring: Optional[Wiring],
                        factory_method: Optional[str],
                        type_hints_locals: Optional[Mapping[str, object]],
                        provider: InjectableProvider = inject.get(InjectableProvider)
                        ) -> None:
    from ...service import Service

    if issubclass(klass, Service):
        raise DuplicateDependencyError(f"{klass} is already defined as a dependency "
                                       f"by inheriting {Service}")

    if wiring is not None:
        wiring.wire(klass=klass, type_hints_locals=type_hints_locals)

    factory: Callable[[], type]
    if factory_method is not None:
        attr = getattr(klass, factory_method)
        raw_attr = klass.__dict__[factory_method]
        if not isinstance(raw_attr, (staticmethod, classmethod)):
            raise TypeError(f"Expected a class/staticmethod for the factory_method, "
                            f"not {type(raw_attr)!r}")
        factory = cast(Callable[[], type], attr)
    else:
        factory = cast(Callable[[], type], klass)  # for mypy...

    provider.register(klass=klass, scope=scope, factory=factory)
