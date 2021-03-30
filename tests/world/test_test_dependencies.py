from contextlib import contextmanager

import pytest

from antidote import Scope, world
from antidote.core.exceptions import DuplicateDependencyError


class Service:
    pass


@contextmanager
def empty_context():
    yield


@pytest.mark.parametrize('context', [empty_context(), world.test.clone()])
def test_invalid_root_world(context):
    with context:
        with pytest.raises(RuntimeError, match=".*test world.*"):
            world.test.singleton(Service, '1')

        with pytest.raises(RuntimeError, match=".*test world.*"):
            @world.test.factory()
            def build() -> Service:
                return Service()


def test_singleton():
    with world.test.empty():
        world.test.singleton("singleton", 12342)
        assert world.get("singleton") == 12342

        world.test.singleton({
            "singleton2": 89,
            "singleton3": 123
        })
        assert world.get("singleton2") == 89
        assert world.get("singleton3") == 123


def test_invalid_singleton():
    with world.test.empty():
        with pytest.raises(TypeError):
            world.test.singleton(1)

        with pytest.raises(TypeError):
            world.test.singleton(dict(), 1)


def test_duplicate_singletons():
    with world.test.empty():
        world.test.singleton("singleton", 12342)

        with pytest.raises(DuplicateDependencyError, match=".*singleton.*12342.*"):
            world.test.singleton("singleton", 1)

        with pytest.raises(DuplicateDependencyError, match=".*singleton.*12342.*"):
            world.test.singleton({"singleton": 1})


def test_factory():
    with world.test.empty():
        s = Service()

        @world.test.factory(Service)
        def build():
            return s

        assert world.get(Service) is s


def test_factory_from_annotation():
    with world.test.empty():
        s = Service()

        @world.test.factory()
        def build() -> Service:
            return s

        assert world.get(Service) is s


def test_factory_singleton():
    with world.test.empty():
        @world.test.factory(Service)
        def build():
            return Service()

        assert world.get(Service) is world.get(Service)

    with world.test.empty():
        @world.test.factory(Service, singleton=True)
        def build2():
            return Service()

        assert world.get(Service) is world.get(Service)

    with world.test.empty():
        @world.test.factory(Service, scope=Scope.singleton())
        def build3():
            return Service()

        assert world.get(Service) is world.get(Service)


def test_factory_no_scope():
    with world.test.empty():
        @world.test.factory(Service, singleton=False)
        def build():
            return Service()

        assert world.get(Service) is not world.get(Service)


def test_factory_scope():
    with world.test.empty():
        scope = world.scopes.new(name='dummy')

        @world.test.factory(Service, scope=scope)
        def build():
            return Service()

        s = world.get(Service)
        assert world.get(Service) is s

        world.scopes.reset(scope)
        assert world.get(Service) is not s


def test_invalid_factory():
    with world.test.empty():
        with pytest.raises(TypeError, match=".*factory.*callable.*"):
            world.test.factory()(object())

        with pytest.raises(ValueError, match="(?i).*either.*dependency.*type hint.*"):
            @world.test.factory()
            def build():
                return Service()
