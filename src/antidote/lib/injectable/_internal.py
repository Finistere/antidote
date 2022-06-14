from __future__ import annotations

from typing import Callable, cast, Mapping, Optional, TypeVar

from ..._internal import API
from ...core import Catalog, inject, LifeTime, Wiring
from ._provider import FactoryProvider

C = TypeVar("C", bound=type)


@API.private
@inject
def register_injectable(
    *,
    klass: type,
    lifetime: Optional[LifeTime],
    wiring: Optional[Wiring],
    factory_method: Optional[str],
    type_hints_locals: Optional[Mapping[str, object]],
    catalog: Catalog,
) -> None:
    if wiring is not None:
        wiring.wire(klass=klass, type_hints_locals=type_hints_locals, catalog=catalog.private)

    factory: Callable[[], type]
    if factory_method is not None:
        attr = getattr(klass, factory_method)
        raw_attr = klass.__dict__[factory_method]
        if not isinstance(raw_attr, (staticmethod, classmethod)):
            raise TypeError(
                f"Expected a class/staticmethod for the factory_method, not {type(raw_attr)!r}"
            )
        factory = cast(Callable[[], type], attr)
    else:
        factory = cast(Callable[[], type], klass)  # for mypy...

    catalog.providers[FactoryProvider].register(
        dependency=klass, factory=factory, lifetime=lifetime
    )
