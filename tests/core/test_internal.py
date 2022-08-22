from typing import cast

import pytest

from antidote import DuplicateDependencyError, new_catalog
from antidote.core._catalog import CatalogImpl


# TODO: testing internal stuff that will be used for future APIs.
def test_register_duplicate_scope_var() -> None:
    catalog = cast(CatalogImpl, new_catalog(include=[]))
    x = object()
    catalog.onion.layer.register_scope_var(x)

    with pytest.raises(DuplicateDependencyError):
        catalog.onion.layer.register_scope_var(x)
