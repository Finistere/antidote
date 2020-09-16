from typing import Hashable, Optional

import pytest

from antidote._internal.utils.world import new_container, ProviderCollection
from antidote.core import DependencyContainer, DependencyInstance
from antidote.core.container import RawDependencyContainer, RawDependencyProvider


class A(RawDependencyProvider):
    def provide(self, dependency: Hashable, container: DependencyContainer
                ) -> Optional[DependencyInstance]:
        if isinstance(dependency, int):
            return DependencyInstance(dependency ** 2)

    def clone(self, keep_singletons_cache: bool) -> 'RawDependencyProvider':
        return A()


@pytest.mark.parametrize('keep_singletons_cache', [True, False])
def test_provider_collection(keep_singletons_cache):
    cleaned_cache = 0

    class B(RawDependencyProvider):
        def __init__(self):
            super().__init__()

        def provide(self, dependency: Hashable, container: DependencyContainer
                    ) -> Optional[DependencyInstance]:
            if isinstance(dependency, str):
                return container.provide(dependency * 2)

        def clone(self, keep_singletons_cache: bool) -> 'RawDependencyProvider':
            nonlocal cleaned_cache
            cleaned_cache += 1
            return B()

    provider = ProviderCollection()
    container = RawDependencyContainer()
    container.update_singletons({'xx': object()})
    assert provider.provide('xx', container) is None

    provider.set_providers([A(), B()])

    for p in [provider, provider.clone(keep_singletons_cache)]:
        assert p.provide(1.23, container) is None
        assert p.provide(9, container).instance == 81
        assert p.provide("x", container).instance == container.get("xx")

    if keep_singletons_cache:
        assert cleaned_cache == 1


def test_new_container():
    assert isinstance(new_container(), DependencyContainer)
