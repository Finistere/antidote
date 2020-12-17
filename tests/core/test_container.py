import pytest

from antidote.core.container import (DependencyInstance, RawContainer,
                                     RawProvider)
from antidote.core.exceptions import DuplicateDependencyError
from antidote.core.utils import DependencyDebug
from antidote.exceptions import (DependencyCycleError, DependencyInstantiationError,
                                 DependencyNotFoundError, FrozenWorldError)
from .utils import DummyFactoryProvider, DummyProvider


class A:
    def __init__(self, *args):
        pass


class B:
    def __init__(self, *args):
        pass


class C:
    def __init__(self, *args):
        pass


class ServiceWithNonMetDependency:
    def __init__(self, dependency):
        pass


@pytest.fixture()
def container():
    return RawContainer()


def test_dependency_repr():
    o = object()
    d = DependencyInstance(o, singleton=False)

    assert repr(False) in repr(d)
    assert repr(o) in repr(d)


def test_add_singletons(container: RawContainer):
    x = object()
    y = object()
    container.add_singletons({'x': x, 'y': y})

    assert container.provide('x').value is x
    assert container.provide('x').singleton is True
    assert container.get('y') is y


def test_duplicate_singletons(container: RawContainer):
    x = object()
    container.add_singletons(dict(x=x))

    with pytest.raises(DuplicateDependencyError):
        container.add_singletons(dict(x=object()))

    # did not change singleton
    assert container.get('x') is x


def test_getitem(container: RawContainer):
    container.add_provider(DummyFactoryProvider)
    container.get(DummyFactoryProvider).data = {
        A: lambda _: A(),
        ServiceWithNonMetDependency: lambda _: ServiceWithNonMetDependency(),
    }
    container.add_provider(DummyProvider)
    container.get(DummyProvider).data = {'name': 'Antidote'}

    assert isinstance(container.get(A), A)
    assert isinstance(container.provide(A), DependencyInstance)
    assert 'Antidote' == container.get('name')
    assert 'Antidote' == container.provide('name').value

    with pytest.raises(DependencyNotFoundError):
        container.get(object)

    with pytest.raises(DependencyInstantiationError):
        container.get(ServiceWithNonMetDependency)


def test_singleton(container: RawContainer):
    container.add_provider(DummyFactoryProvider)
    container.get(DummyFactoryProvider).data = {
        A: lambda _: A(),
        B: lambda _: B(),
    }

    service = container.get(A)
    assert container.get(A) is service
    assert container.provide(A).value is service
    assert container.provide(A).singleton is True

    container.get(DummyFactoryProvider).singleton = False
    another_service = container.get(B)
    assert container.get(B) is not another_service
    assert container.provide(B).value is not another_service
    assert container.provide(B).singleton is False

    assert container.get(A) == service


def test_dependency_cycle_error(container: RawContainer):
    container.add_provider(DummyFactoryProvider)
    container.get(DummyFactoryProvider).data = {
        A: lambda _: container.get(B),
        B: lambda _: container.get(C),
        C: lambda _: container.get(A),
    }

    with pytest.raises(DependencyCycleError):
        container.get(A)

    with pytest.raises(DependencyCycleError):
        container.get(B)

    with pytest.raises(DependencyCycleError):
        container.get(C)


def test_dependency_instantiation_error(container: RawContainer):
    container.add_provider(DummyFactoryProvider)

    def raise_error():
        raise RuntimeError()

    container.get(DummyFactoryProvider).data = {
        A: lambda _: container.get(B),
        B: lambda _: container.get(C),
        C: lambda _: raise_error(),
    }

    with pytest.raises(DependencyInstantiationError, match=".*C.*"):
        container.get(C)

    with pytest.raises(DependencyInstantiationError, match=".*A.*"):
        container.get(A)


def test_providers(container: RawContainer):
    x = object()
    container.add_provider(DummyProvider)
    container.get(DummyProvider).data = dict(x=x)
    container.add_provider(DummyFactoryProvider)
    container.get(DummyFactoryProvider).data = dict(y=lambda c: c.get('y'))

    assert len(container.providers) == 2
    for provider in container.providers:
        if isinstance(provider, DummyProvider):
            assert provider.data == dict(x=x)
        else:
            assert 'y' in provider.data


def test_repr_str(container: RawContainer):
    container.add_provider(DummyProvider)
    container.get(DummyProvider).data = {'name': 'Antidote'}
    container.add_singletons({'test': 1})

    assert 'test' in repr(container)
    assert repr(container.get(DummyProvider)) in repr(container)
    assert str(container.get(DummyProvider)) in str(container)


def test_invalid_provider(container: RawContainer):
    with pytest.raises(TypeError):
        container.add_provider(object)

    # Cannot register twice the same kind of provider
    container.add_provider(DummyProvider)
    with pytest.raises(ValueError):
        container.add_provider(DummyProvider)


def test_clone(container: RawContainer):
    container.add_provider(DummyProvider)
    container.get(DummyProvider).data = {'name': 'Antidote'}
    container.add_singletons({'test': object()})

    cloned = container.clone(keep_singletons=True)
    assert cloned.get('test') is container.get('test')
    assert cloned.get(DummyProvider) is not container.get(DummyProvider)

    cloned.add_singletons({'test2': 2})
    with pytest.raises(DependencyNotFoundError):
        container.get("test2")

    cloned = container.clone(keep_singletons=False)
    with pytest.raises(DependencyNotFoundError):
        cloned.get("test")
    assert cloned.get(DummyProvider) is not container.get(DummyProvider)

    cloned.add_singletons({'test2': 2})
    with pytest.raises(DependencyNotFoundError):
        container.get("test2")


def test_freeze(container: RawContainer):
    container.add_provider(DummyProvider)
    container.get(DummyProvider).data = {'name': 'Antidote'}
    container.freeze()

    with pytest.raises(FrozenWorldError):
        container.add_provider(DummyFactoryProvider)

    with pytest.raises(FrozenWorldError):
        container.add_singletons({'test': object()})


def test_ensure_not_frozen(container: RawContainer):
    with container.ensure_not_frozen():
        pass

    container.freeze()

    with pytest.raises(FrozenWorldError):
        with container.ensure_not_frozen():
            pass


def test_provider_property(container: RawContainer):
    container.add_provider(DummyProvider)
    assert container.providers == [container.get(DummyProvider)]


def test_providers_must_properly_clone(container: RawContainer):
    class DummySelf(RawProvider):
        def clone(self, keep_singletons_cache: bool) -> 'RawProvider':
            return self

    container.add_provider(DummySelf)

    with pytest.raises(RuntimeError, match="(?i).*provider.*instance.*"):
        container.clone()


def test_providers_must_properly_clone2(container: RawContainer):
    container.add_provider(DummyProvider)
    p = container.get(DummyProvider)

    class DummyRegistered(RawProvider):
        def clone(self, keep_singletons_cache: bool) -> 'RawProvider':
            return p

    container.add_provider(DummyRegistered)
    with pytest.raises(RuntimeError, match="(?i).*provider.*fresh instance.*"):
        container.clone()


def test_clone_providers(container: RawContainer):
    container.add_provider(DummyProvider)
    data = dict(name='antidote')
    container.get(DummyProvider).data = data

    cloned = container.clone(clone_providers=True)
    assert cloned.get(DummyProvider).data == data

    cloned2 = container.clone(clone_providers=False)
    assert cloned2.get(DummyProvider).data is None


@pytest.mark.filterwarnings("ignore:Debug information")
def test_raise_if_exists(container: RawContainer):
    container.raise_if_exists(1)  # Nothing should happen

    container.add_singletons({1: 10})
    with pytest.raises(DuplicateDependencyError, match=".*singleton.*10.*"):
        container.raise_if_exists(1)

    container.add_provider(DummyProvider)
    container.get(DummyProvider).data = {'name': 'Antidote'}
    with pytest.raises(DuplicateDependencyError, match=".*DummyProvider.*"):
        container.raise_if_exists('name')

    class DummyProviderWithDebug(DummyProvider):
        def debug(self, dependency) -> DependencyDebug:
            return DependencyDebug("debug_info", singleton=True)

    container.add_provider(DummyProviderWithDebug)
    container.get(DummyProviderWithDebug).data = {'hello': 'world'}
    with pytest.raises(DuplicateDependencyError,
                       match=".*DummyProviderWithDebug.*\\ndebug_info"):
        container.raise_if_exists('hello')
