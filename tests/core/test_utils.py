from antidote import world
from antidote.core import Dependency


def test_dependency():
    with world.test.empty():
        world.singletons.set('x', object())
        d = Dependency('x')
        assert d.value == 'x'
        assert d.get() is world.get('x')
