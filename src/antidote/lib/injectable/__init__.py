from __future__ import annotations

from ..._internal import API
from ...core import Catalog
from .injectable import injectable

__all__ = ["antidote_injectable", "injectable"]


@API.public
def antidote_injectable(catalog: Catalog) -> None:
    from ._provider import FactoryProvider

    if FactoryProvider not in catalog.providers:
        catalog.include(FactoryProvider)
