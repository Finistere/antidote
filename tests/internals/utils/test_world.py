from typing import Hashable, Optional

import pytest

from antidote._internal.utils.world import new_container, OverridableProviderCollection
from antidote.core import Container, DependencyInstance
from antidote.core.container import RawContainer, RawProvider


class A(RawProvider):

    def exists(self, dependency: Hashable) -> bool:
        return isinstance(dependency, int)

    def maybe_provide(self, dependency: Hashable, container: Container
                      ) -> Optional[DependencyInstance]:
        if isinstance(dependency, int):
            return DependencyInstance(dependency ** 2)

    def clone(self, keep_singletons_cache: bool) -> 'RawProvider':
        return A()


@pytest.mark.parametrize('keep_singletons_cache', [True, False])
def test_provider_collection(keep_singletons_cache):
    cleaned_cache = 0

    class B(RawProvider):
        def __init__(self):
            super().__init__()

        def exists(self, dependency: Hashable) -> bool:
            return isinstance(dependency, str)

        def maybe_provide(self, dependency: Hashable, container: Container
                          ) -> Optional[DependencyInstance]:
            if isinstance(dependency, str):
                return container.provide(dependency * 2)

        def clone(self, keep_singletons_cache: bool) -> 'RawProvider':
            nonlocal cleaned_cache
            cleaned_cache += 1
            return B()

    provider = OverridableProviderCollection()
    container = RawContainer()
    container.add_singletons({'xx': object()})
    assert provider.maybe_provide('xx', container) is None

    provider.set_providers([A(), B()])

    for p in [provider, provider.clone(keep_singletons_cache)]:
        assert p.maybe_provide(1.23, container) is None
        assert p.maybe_provide(9, container).value == 81
        assert p.maybe_provide("x", container).value == container.get("xx")

    if keep_singletons_cache:
        assert cleaned_cache == 1


def test_new_container():
    assert isinstance(new_container(), Container)
