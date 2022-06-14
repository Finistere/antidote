from __future__ import annotations

from typing import cast, TYPE_CHECKING

from ._catalog import AppCatalog, CatalogImpl
from ._inject import InjectorImpl
from ._wrapper import current_catalog_context
from .utils import new_catalog

if TYPE_CHECKING:
    from . import Injector, PublicCatalog, ReadOnlyCatalog

world: PublicCatalog = new_catalog(name="world", include=[])  # antidote_lib included later
inject: Injector = InjectorImpl()
app_catalog: ReadOnlyCatalog = AppCatalog()
current_catalog_context.set(cast(CatalogImpl, world).internal)
