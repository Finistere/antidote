import pytest

from antidote import world
from antidote._providers import (FactoryProvider, IndirectProvider,
                                 LazyProvider, ServiceProvider)
from antidote.core.container import RawProvider


@pytest.fixture(params=[
    FactoryProvider,
    ServiceProvider,
    LazyProvider,
    IndirectProvider
])
def provider(request):
    return request.param()


def test_unknown_dependency(provider: RawProvider):
    assert world.test.maybe_provide_from(provider, object()) is None
    assert provider.maybe_debug(object()) is None
    assert not provider.exists(object())


def test_clone(provider: RawProvider):
    assert isinstance(provider.clone(False), type(provider))
