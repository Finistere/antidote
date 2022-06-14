from ..core import Catalog
from .injectable import antidote_injectable
from .interface import antidote_interface
from .lazy import antidote_lazy


def antidote_lib(catalog: Catalog) -> None:
    catalog.include(antidote_lazy)
    catalog.include(antidote_injectable)
    catalog.include(antidote_interface)
