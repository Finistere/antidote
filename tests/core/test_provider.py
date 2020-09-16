from __future__ import annotations

from contextlib import contextmanager
from typing import Hashable, Optional

import pytest

from antidote import world
from antidote.core import DependencyContainer, DependencyInstance, DependencyProvider, \
    does_not_freeze, StatelessDependencyProvider, Wiring
from antidote.exceptions import FrozenWorldError


@contextmanager
def does_not_raise():
    yield


def test_freeze_world():
    class DummyProvider(DependencyProvider):
        def provide(self, dependency: Hashable, container: DependencyContainer
                    ) -> Optional[DependencyInstance]:
            return None

        def clone(self) -> DummyProvider:
            return self

        def register(self):
            return "register"

        @does_not_freeze
        def method(self):
            return "method"

        @staticmethod
        def static():
            return "static"

        @classmethod
        def klass(cls):
            return "klass"

    provider = DummyProvider()
    assert provider.register() == "register"
    assert provider.method() == "method"
    assert provider.static() == "static"
    assert provider.klass() == "klass"

    with world.test.empty():
        world.provider(DummyProvider)
        provider = world.get[DummyProvider]()
        assert provider.register() == "register"
        assert provider.method() == "method"
        assert provider.static() == "static"
        assert provider.klass() == "klass"

        world.freeze()
        assert provider.method() == "method"
        assert provider.static() == "static"
        assert provider.klass() == "klass"
        provider.clone()
        provider.provide(None, None)
        with pytest.raises(FrozenWorldError):
            provider.register()


def test_stateless():
    class DummyProvider(StatelessDependencyProvider):
        def provide(self, dependency: Hashable, container: DependencyContainer
                    ) -> Optional[DependencyInstance]:
            return None

    p = DummyProvider()
    assert p.clone(True) is not p
    assert isinstance(p.clone(False), DummyProvider)
