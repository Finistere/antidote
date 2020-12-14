from typing import Any, Callable, Hashable, Optional

import pytest

from antidote import world
from antidote.core import DependencyInstance
from antidote.core.exceptions import DuplicateDependencyError
from antidote.exceptions import DependencyNotFoundError
from ..core.utils import DummyProvider

sentinel = object()


@pytest.mark.parametrize('override', [
    pytest.param(lambda d, v: world.test.override.singleton(d, v), id='singleton'),
    pytest.param(lambda d, v: world.test.override.singleton({d: v}), id='singletons')
])
def test_singleton(override: Callable[[Any, Any], Any]):
    with world.test.empty():
        with world.test.clone(overridable=True):
            override('test', 'a')
            assert world.get("test") == 'a'

            # Still works, but has no impact as it has been overridden
            world.singletons.add('test', sentinel)
            assert world.get("test") == 'a'

        world.singletons.add("test", sentinel)

        with world.test.clone(overridable=True):
            override("test", 'a')
            assert world.get("test") == 'a'

            # double override works
            override("test", 'b')
            assert world.get("test") == 'b'

        assert world.get('test') is sentinel

        with world.test.clone(overridable=True, keep_singletons=True):
            assert world.get('test') is sentinel

            override("test", 'a')
            assert world.get("test") == 'a'

            with pytest.raises(DuplicateDependencyError):
                # already existed in the container without overrides.
                world.singletons.add("test", 2)

        assert world.get('test') is sentinel


def test_factory():
    # overrides normal provider
    with world.test.clone(overridable=True):
        world.provider(DummyProvider)
        p = world.get[DummyProvider]()
        p.data = {'test': sentinel}

        assert world.get('test') is sentinel

        @world.test.override.factory('test')
        def f():
            return 'a'

        assert world.get('test') == 'a'

        @world.test.override.factory('test')
        def g():
            return 'b'

        assert world.get('test') == 'b'

    # overrides singletons
    with world.test.clone(overridable=True):
        world.singletons.add("test", sentinel)
        assert world.get('test') is sentinel

        @world.test.override.factory('test')
        def f1():
            return 'a'

        assert world.get('test') == 'a'

    # non singleton
    with world.test.clone(overridable=True):
        @world.test.override.factory('test')
        def f2():
            return object()

        assert world.get('test') is not world.get('test')

    # singleton
    with world.test.clone(overridable=True):
        @world.test.override.factory('test', singleton=True)
        def f3():
            return object()

        assert world.get('test') is world.get('test')


def test_provider():
    # overrides normal provider
    with world.test.clone(overridable=True):
        world.provider(DummyProvider)
        p = world.get[DummyProvider]()
        p.data = {'test': sentinel, 'test2': sentinel}

        assert world.get('test') is sentinel
        assert world.get('test2') is sentinel

        @world.test.override.provider
        def f(dependency: Hashable) -> Optional[DependencyInstance]:
            if dependency == 'test':
                return DependencyInstance('a')

        assert world.get('test') == 'a'
        assert world.get('test2') is sentinel

    # overrides singletons
    with world.test.clone(overridable=True):
        world.singletons.add({'test': sentinel, 'test2': sentinel})

        assert world.get('test') is sentinel
        assert world.get('test2') is sentinel

        @world.test.override.provider
        def f2(dependency: Hashable) -> Optional[DependencyInstance]:
            if dependency == 'test':
                return DependencyInstance('a')

        assert world.get('test') == 'a'
        assert world.get('test2') is sentinel

    # non singleton dependency
    with world.test.clone(overridable=True):

        @world.test.override.provider
        def f3(dependency: Hashable) -> Optional[DependencyInstance]:
            if dependency == 'test':
                return DependencyInstance(object(), singleton=False)

        assert world.get('test') is not world.get('test')

    # singleton dependency
    with world.test.clone(overridable=True):

        @world.test.override.provider
        def f4(dependency: Hashable) -> Optional[DependencyInstance]:
            if dependency == 'test':
                return DependencyInstance(object(), singleton=True)

        assert world.get('test') is world.get('test')


def test_deep_clone():
    with world.test.empty():
        world.singletons.add("test", sentinel)

        with world.test.clone(overridable=True, keep_singletons=True):
            with world.test.clone(overridable=True, keep_singletons=False):
                with pytest.raises(DependencyNotFoundError):
                    world.get("test")

        with world.test.clone(overridable=True):
            world.test.override.singleton("test", 'a')
            with world.test.clone(overridable=True, keep_singletons=False):
                with pytest.raises(DependencyNotFoundError):
                    world.get("test")

            with world.test.clone(overridable=False, keep_singletons=False):
                with pytest.raises(DependencyNotFoundError):
                    world.get("test")

        with world.test.clone(overridable=True):
            world.test.override.singleton("test", 'a')
            with world.test.clone(overridable=True, keep_singletons=True):
                assert world.get("test") == 'a'

            with world.test.clone(overridable=False, keep_singletons=True):
                assert world.get("test") == 'a'


def test_debug():
    with world.test.clone(overridable=True):
        from antidote._internal import state

        world.singletons.add("test", sentinel)

        world.test.override.singleton("over", 1)

        @world.test.override.factory('factory')
        def f():
            return 2

        c = state.get_container()
        assert "Override" not in c.debug("test").info
        assert "Singleton" in c.debug("test").info

        assert "Override" in c.debug("over").info
        assert "Singleton" in c.debug("over").info

        assert "Override" in c.debug("factory").info
        assert "Factory" in c.debug("factory").info


def test_invalid():
    with world.test.clone(overridable=True):
        with pytest.raises(TypeError):
            world.test.override.singleton(1)

        with pytest.raises(TypeError):
            world.test.override.singleton(dict(), 1)

        with pytest.raises(TypeError):
            @world.test.override.factory('test', singleton=object())
            def f():
                pass

        with pytest.raises(TypeError):
            world.test.override.factory('test', singleton=True)(object())

        with pytest.raises(TypeError):
            world.test.override.provider(object())
