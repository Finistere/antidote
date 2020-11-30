import pytest

from antidote.core.container import (DependencyInstance, OverridableRawContainer,
                                     RawContainer)
from antidote.core.exceptions import DependencyCycleError, DependencyInstantiationError
from antidote.exceptions import (DependencyNotFoundError)
from .utils import DummyProvider


@pytest.fixture
def original_container():
    c = RawContainer()
    c.add_provider(DummyProvider)
    c.get(DummyProvider).data = {'name': 'Antidote'}
    c.add_singletons({'singleton': 'yes'})
    return c


@pytest.fixture
def container(original_container):
    return OverridableRawContainer.build(original_container, keep_singletons=True)


@pytest.mark.parametrize('keep_singletons', [True, False])
def test_build(original_container: RawContainer, keep_singletons: bool):
    container = OverridableRawContainer.build(original_container,
                                              keep_singletons=keep_singletons)
    assert container.get('name') == "Antidote"
    if keep_singletons:
        assert container.get('singleton') == 'yes'
    else:
        with pytest.raises(DependencyNotFoundError):
            container.get('singleton')


def test_override_singletons(container: OverridableRawContainer):
    assert container.get('name') == "Antidote"
    assert container.get('singleton') == 'yes'

    for dep in ['name', 'singleton']:
        container.override_singletons({dep: 'different'})
        assert container.get(dep) == 'different'
        container.override_singletons({dep: 'different-v2'})
        assert container.get(dep) == 'different-v2'
        assert container.provide(dep) == DependencyInstance('different-v2',
                                                            singleton=True)


def test_override_factory(container: OverridableRawContainer):
    assert container.get('name') == "Antidote"
    assert container.get('singleton') == 'yes'

    for dep in ['name', 'singleton']:
        container.override_factory(dep, factory=lambda: 'different', singleton=False)
        assert container.get(dep) == 'different'
        container.override_factory(dep, factory=lambda: 'different-v2', singleton=False)
        assert container.get(dep) == 'different-v2'
        assert container.provide(dep) == DependencyInstance('different-v2',
                                                            singleton=False)

        container.override_factory(dep, factory=lambda: object(), singleton=True)
        value = container.get(dep)
        assert not isinstance(value, str)
        assert container.get(dep) is value

        container.override_factory(dep, factory=lambda: object(), singleton=True)
        # didn't change anything, because it's now a singleton.
        assert container.get(dep) is value

        container.override_singletons({dep: 'Hello'})
        assert container.get(dep) == 'Hello'


def test_override_provider(container: OverridableRawContainer):
    assert container.get('name') == "Antidote"
    assert container.get('singleton') == 'yes'

    for dep in ['name', 'singleton']:
        container.override_provider(
            lambda x: DependencyInstance('different') if x == dep else None)
        assert container.get(dep) == 'different'
        container.override_provider(
            lambda x: DependencyInstance('different-v2') if x == dep else None)
        assert container.get(dep) == 'different-v2'
        assert container.provide(dep) == DependencyInstance('different-v2',
                                                            singleton=False)

        with pytest.raises(DependencyNotFoundError):
            container.get('x')  # new provider does not bring any other value

        container.override_provider(
            lambda x: DependencyInstance(object(),
                                         singleton=True) if x == dep else None)
        value = container.get(dep)
        assert not isinstance(value, str)
        assert container.get(dep) is value

        container.override_provider(
            lambda x: DependencyInstance(object(),
                                         singleton=True) if x == dep else None)
        # didn't change anything, because it's now a singleton.
        assert container.get(dep) is value

        container.override_singletons({dep: 'Hello'})
        assert container.get(dep) == 'Hello'


def test_invalid_override_singletons(container: OverridableRawContainer):
    with pytest.raises(TypeError, match='.*singletons.*'):
        container.override_singletons(object())


def test_invalid_override_factory(container: OverridableRawContainer):
    with pytest.raises(TypeError, match='.*factory.*'):
        container.override_factory(object(), factory=object(), singleton=True)
    with pytest.raises(TypeError, match='.*singleton.*'):
        container.override_factory(object(), factory=lambda: None, singleton=object())


def test_invalid_override_provider(container: OverridableRawContainer):
    with pytest.raises(TypeError, match='.*provider.*'):
        container.override_provider(object())


def test_errors(container: OverridableRawContainer):
    container.override_factory('cycle', factory=lambda: container.get('cycle'),
                               singleton=False)
    with pytest.raises(DependencyCycleError):
        container.get('cycle')

    def factory():
        raise RuntimeError()

    container.override_factory('error', factory=factory, singleton=False)
    with pytest.raises(DependencyInstantiationError):
        container.get('error')
