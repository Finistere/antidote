import re

import pytest

from antidote.core import (
    app_catalog,
    CatalogId,
    DependencyNotFoundError,
    inject,
    new_catalog,
    world,
)
from tests.utils import Obj

x = Obj()
y = Obj()


def test_current_catalog_world() -> None:
    with world.test.empty() as overrides:
        overrides[x] = x

        assert x in app_catalog
        assert app_catalog[x] is x
        assert app_catalog.get(x) is x

        assert y not in app_catalog
        assert app_catalog.get(y) is None
        assert app_catalog.get(y, default=y) is y

        with pytest.raises(DependencyNotFoundError, match=re.escape(repr(y))):
            app_catalog[y]

        assert app_catalog.debug(x) == world.debug(x)
        assert app_catalog.debug(y) == world.debug(y)

        assert app_catalog.id == world.id
        assert app_catalog.is_frozen == world.is_frozen
        world.freeze()
        assert app_catalog.is_frozen == world.is_frozen

        assert str(world.id) in str(app_catalog)
        assert str(world.id) in repr(app_catalog)


def test_current_catalog_injection() -> None:
    catalog = new_catalog(include=[])

    assert app_catalog.id == world.id

    @inject
    def f1(a: object = inject.get(x)) -> CatalogId:
        return app_catalog.id

    @inject(catalog=catalog)
    def f2(a: object = inject.get(x)) -> CatalogId:
        return app_catalog.id

    assert f1() == world.id
    assert f2() == catalog.id
