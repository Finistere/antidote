from __future__ import annotations

from ..._internal import API
from ...core import Catalog
from ._constant import ConstImpl
from ._lazy import LazyImpl
from .constant import Const, is_const_factory
from .lazy import is_lazy, Lazy, LazyFunction, LazyMethod, LazyProperty

__all__ = [
    "const",
    "lazy",
    "Lazy",
    "is_lazy",
    "is_const_factory",
    "antidote_lazy",
    "LazyFunction",
    "LazyProperty",
    "LazyMethod",
]

const: Const = ConstImpl()
lazy: Lazy = LazyImpl()


@API.public
def antidote_lazy(catalog: Catalog) -> None:
    from ._provider import LazyProvider

    if LazyProvider not in catalog.providers:
        catalog.include(LazyProvider)
