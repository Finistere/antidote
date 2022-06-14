from __future__ import annotations

from typing import Callable, Iterable, Type, TYPE_CHECKING

from typing_extensions import TypeGuard

from .._internal import API, auto_detect_var_name, Default, enforce_valid_name
from .provider import Provider

if TYPE_CHECKING:
    from . import Catalog, PublicCatalog, ReadOnlyCatalog

__all__ = ["is_catalog", "is_compiled", "new_catalog", "is_readonly_catalog"]


@API.public
def is_compiled() -> bool:
    """
    Whether current Antidote implementations is the compiled (Cython) version or not
    """
    return False


@API.experimental
def new_catalog(
    *,
    name: str | Default = Default.sentinel,
    include: Iterable[Callable[[Catalog], object] | PublicCatalog | Type[Provider]]
    | Default = Default.sentinel,
) -> PublicCatalog:
    """
    Creates a new :py:class:`.PublicCatalog`. It's recommended to provide a name to the catalog to
    better differentiate it from others. It's possible to provide an iterable of functions or
    public catalogs to :py:class:`~.Catalog.include`.
    """
    from .._internal import auto_detect_origin_frame
    from ._catalog import CatalogImpl

    if isinstance(name, Default):
        name, origin = auto_detect_var_name().rsplit("@", 1)
    else:
        enforce_valid_name(name)
        origin = auto_detect_origin_frame()

    catalog = CatalogImpl.create_public(name=name, origin=origin)
    if isinstance(include, Default):
        from ..lib import antidote_lib

        catalog.include(antidote_lib)
    else:
        for x in include:
            catalog.include(x)
    return catalog


@API.public
def is_catalog(catalog: object) -> TypeGuard[Catalog]:
    """
    Returns whether the specified object is a :py:class:`.Catalog` or not.
    """
    from ._catalog import CatalogImpl

    return isinstance(catalog, CatalogImpl)


@API.public
def is_readonly_catalog(catalog: object) -> TypeGuard[ReadOnlyCatalog]:
    """
    Returns whether the specified object is a :py:class:`.ReadOnlyCatalog` or not.
    """
    from ._catalog import AppCatalog, ReadOnlyCatalogImpl

    return isinstance(catalog, (AppCatalog, ReadOnlyCatalogImpl))
