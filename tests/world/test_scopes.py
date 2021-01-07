import pytest

from antidote import world, Scope


@pytest.fixture(autouse=True)
def empty_world():
    with world.test.empty():
        yield


def test_new():
    s = world.scopes.new("test")
    assert isinstance(s, Scope)
    assert s.name == "test"


@pytest.mark.parametrize('expectation,name', [
    (pytest.raises(TypeError, match=".*name.*str.*"), object()),
    (pytest.raises(ValueError, match=".*reserved.*"), Scope.singleton().name),
    (pytest.raises(ValueError, match=".*reserved.*"), Scope.sentinel().name),
    (pytest.raises(ValueError, match=".*empty.*"), "")
])
def test_invalid_new_scope_name(expectation, name):
    with expectation:
        world.scopes.new(name)


def test_no_duplicate_scope():
    world.scopes.new("dummy")
    with pytest.raises(ValueError, match=".*already exists.*"):
        world.scopes.new("dummy")


def test_reset():
    s = world.scopes.new("dummy")
    world.scopes.reset(s)  # should just work, the reset() is tested directly in providers


@pytest.mark.parametrize('expectation,scope', [
    (pytest.raises(TypeError, match=".*scope.*Scope.*"), object()),
    (pytest.raises(ValueError, match=".*Cannot reset.*"), Scope.singleton()),
    (pytest.raises(ValueError, match=".*Cannot reset.*"), Scope.sentinel())
])
def test_invalid_reset(expectation, scope):
    with expectation:
        world.scopes.reset(scope)


def test_reset_unknown_scope():
    s = world.scopes.new('1')

    with world.test.empty():
        with pytest.raises(ValueError, match=".*Unknown.*"):
            world.scopes.reset(s)
