from __future__ import annotations

from typing import Any, cast, TYPE_CHECKING

from ._catalog import AppCatalogProxy
from ._inject import InjectImpl
from ._raw import current_catalog_onion
from .utils import new_catalog

if TYPE_CHECKING:
    from . import Inject, PublicCatalog, ReadOnlyCatalog

world: PublicCatalog = new_catalog(name="world", include=[])  # antidote_lib included later
inject: Inject = InjectImpl()
app_catalog: ReadOnlyCatalog = AppCatalogProxy()
current_catalog_onion.set(cast(Any, world).onion)
