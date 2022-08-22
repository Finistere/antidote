from ..core import Catalog
from .injectable_ext import antidote_lib_injectable
from .interface_ext import antidote_lib_interface
from .lazy_ext import antidote_lib_lazy


def antidote_lib(catalog: Catalog) -> None:
    catalog.include(antidote_lib_lazy)
    catalog.include(antidote_lib_injectable)
    catalog.include(antidote_lib_interface)
