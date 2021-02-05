from contextlib import contextmanager

import pytest

from antidote import Scope
from antidote.utils import validated_scope

dummy_scope = Scope('dummy')


@contextmanager
def does_not_raise():
    yield


@pytest.mark.parametrize('expectation, kwargs', [
    pytest.param(pytest.raises(TypeError, match='.*scope.*'),
                 dict(scope=object(), default=None),
                 id='scope=object'),
    pytest.param(pytest.raises(TypeError, match='.*default.*'),
                 dict(scope=None, default=object()),
                 id='default=object'),
    pytest.param(pytest.raises(TypeError, match='.*singleton.*'),
                 dict(scope=Scope.sentinel(), singleton=object(), default=None),
                 id='singleton=object'),
    pytest.param(pytest.raises(TypeError, match='.*both.*'),
                 dict(scope=None, singleton=False, default=None),
                 id='singleton & scope'),
])
def test_invalid_validated_scope(expectation, kwargs):
    with expectation:
        assert validated_scope(**kwargs)


@pytest.mark.parametrize('scope, singleton, default, expected', [
    pytest.param(Scope.sentinel(), True, None, Scope.singleton(), id='singleton=True'),
    pytest.param(Scope.sentinel(), False, None, None, id='singleton=False'),
    pytest.param(None, None, None, None, id='scope=None'),
    pytest.param(Scope.singleton(), None, None, Scope.singleton(), id='scope=singleton'),
    pytest.param(dummy_scope, None, None, dummy_scope, id='scope=dummy'),
    pytest.param(Scope.sentinel(), None, None, None, id='default=None'),
    pytest.param(Scope.sentinel(), None, Scope.singleton(), Scope.singleton(),
                 id='default=singleton'),
    pytest.param(Scope.sentinel(), None, dummy_scope, dummy_scope, id='default=dummy'),
])
def test_validated_scope(scope, singleton, default, expected):
    assert expected == validated_scope(scope, singleton, default=default)
