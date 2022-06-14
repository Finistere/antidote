import pytest

from antidote import DuplicateDependencyError, new_catalog
from antidote.core._internal_catalog import InternalCatalog


# TODO: testing internal stuff that will be used for future APIs.
def test_register_duplicate_scope_var() -> None:
    catalog = new_catalog(include=[])
    internal: InternalCatalog = catalog.internal  # type: ignore
    x = object()
    internal.register_scope_var(x)

    with pytest.raises(DuplicateDependencyError):
        internal.register_scope_var(x)
