import pytest

from antidote.core.container import (DependencyValue, OverridableRawContainer,
                                     RawContainer, Scope)
from antidote.exceptions import (DependencyCycleError, DependencyInstantiationError,
                                 DependencyNotFoundError)
from .utils import DummyProvider


@pytest.fixture
def original_container():
    c = RawContainer()
    c.add_provider(DummyProvider)
    c.get(DummyProvider).data = {'name': 'Antidote'}
    return c


@pytest.fixture
def container(original_container):
    return original_container.clone(keep_singletons=True,
                                    keep_scopes=False)


def test_override_singletons(container: OverridableRawContainer):
    assert container.get('name') == "Antidote"

    container.override_singletons({'name': 'different'})
    assert container.get('name') == 'different'
    container.override_singletons({'name': 'different-v2'})
    assert container.get('name') == 'different-v2'
    assert container.provide('name') == DependencyValue('different-v2',
                                                        scope=Scope.singleton())


def test_override_factory(container: OverridableRawContainer):
    assert container.get('name') == "Antidote"

    container.override_factory('name', factory=lambda: 'different', scope=None)
    assert container.get('name') == 'different'
    container.override_factory('name', factory=lambda: 'different-v2', scope=None)
    assert container.get('name') == 'different-v2'
    assert container.provide('name') == DependencyValue('different-v2',
                                                        scope=None)

    # overriding previous factory which had no scope
    container.override_factory('name', factory=lambda: object(), scope=Scope.singleton())
    value = container.get('name')
    assert not isinstance(value, str)
    assert container.get('name') is value

    # override still works
    container.override_factory('name', factory=lambda: object(), scope=Scope.singleton())
    assert container.get('name') is not value

    container.override_singletons({'name': 'Hello'})
    assert container.get('name') == 'Hello'


def test_override_provider(container: OverridableRawContainer):
    assert container.get('name') == "Antidote"

    container.override_provider(
        lambda x: DependencyValue('different') if x == 'name' else None)
    assert container.get('name') == 'different'
    container.override_provider(
        lambda x: DependencyValue('different-v2') if x == 'name' else None)
    assert container.get('name') == 'different-v2'
    assert container.provide('name') == DependencyValue('different-v2',
                                                        scope=None)

    with pytest.raises(DependencyNotFoundError):
        container.get('x')  # new provider does not bring any other value

    # overriding previous provider which had no scope
    container.override_provider(
        lambda x: DependencyValue(object(),
                                  scope=Scope.singleton()) if x == 'name' else None)
    value = container.get('name')
    assert not isinstance(value, str)
    assert container.get('name') is value

    container.override_provider(
        lambda x: DependencyValue(object(),
                                  scope=Scope.singleton()) if x == 'name' else None)
    # didn't change anything, because it's now a singleton.
    assert container.get('name') is value

    container.override_singletons({'name': 'Hello'})
    assert container.get('name') == 'Hello'


def test_errors(container: OverridableRawContainer):
    container.override_factory('cycle', factory=lambda: container.get('cycle'),
                               scope=None)
    with pytest.raises(DependencyCycleError):
        container.get('cycle')

    def factory():
        raise RuntimeError()

    container.override_factory('error', factory=factory, scope=None)
    with pytest.raises(DependencyInstantiationError):
        container.get('error')
