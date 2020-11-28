from contextlib import contextmanager
from typing import Hashable, Optional

import pytest

from antidote import world
from antidote.core import Container, DependencyInstance, does_not_freeze, Provider, \
    StatelessProvider
from antidote.exceptions import FrozenWorldError


@contextmanager
def does_not_raise():
    yield


def test_freeze_world():
    class DummyProvider(Provider):
        def provide(self, dependency: Hashable, container: Container
                    ) -> Optional[DependencyInstance]:
            return None

        def clone(self, keep_singletons_cache: bool) -> 'DummyProvider':
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
        provider.clone(False)
        provider.provide(None, None)
        with pytest.raises(FrozenWorldError):
            provider.register()


def test_stateless():
    class DummyProvider(StatelessProvider):
        def provide(self, dependency: Hashable, container: Container
                    ) -> Optional[DependencyInstance]:
            return None

    p = DummyProvider()
    assert p.clone(True) is not p
    assert isinstance(p.clone(False), DummyProvider)


def test_no_default_implementation():
    class Dummy(Provider):
        pass

    with pytest.raises(NotImplementedError):
        Dummy().maybe_provide(object(), object())

    with pytest.raises(NotImplementedError):
        Dummy().exists(object())

    with pytest.raises(NotImplementedError):
        Dummy().clone(False)

    with pytest.raises(RuntimeError):
        Dummy().provide(object(), object())

    with pytest.raises(NotImplementedError):
        Dummy().exists(False)


def test_debug():
    x = object()

    class Dummy(Provider):
        def exists(self, dependency: Hashable) -> bool:
            return dependency is x

    Dummy().maybe_debug(object())  # should no fail
    with pytest.warns(UserWarning, match="(?i).*debug.*"):
        Dummy().maybe_debug(x)
