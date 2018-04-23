import pytest

from antidote import Instance, DependencyContainer, Dependency
from antidote import (
    DependencyCycleError, DependencyInstantiationError,
    DependencyNotFoundError, DependencyNotProvidableError
)


class DummyProvider(object):
    singleton = True

    def __init__(self, data=None):
        self.data = data or dict()

    def __setitem__(self, key, value):
        self.data[key] = value

    def __antidote_provide__(self, dependency_id, *args, **kwargs):
        try:
            return Instance(self.data[dependency_id],
                            singleton=self.singleton)
        except KeyError:
            raise DependencyNotProvidableError(dependency_id)


class DummyFactoryProvider(object):
    create_singleton = True

    def __init__(self, data=None):
        self.data = data or dict()

    def __setitem__(self, key, value):
        self.data[key] = value

    def __antidote_provide__(self, dependency_id, *args, **kwargs):
        try:
            return Instance(self.data[dependency_id](),
                            singleton=self.create_singleton)
        except KeyError:
            raise DependencyNotProvidableError(dependency_id)


class Service(object):
    def __init__(self, *args):
        pass


class AnotherService(object):
    def __init__(self, *args):
        pass


class YetAnotherService(object):
    def __init__(self, *args):
        pass


class ServiceWithNonMetDependency(object):
    def __init__(self, dependency):
        pass


@pytest.fixture()
def container():
    return DependencyContainer()


def test_dependency_repr():
    o = object()
    d = Instance(o, False)

    assert repr(False) in repr(d)
    assert repr(o) in repr(d)


def test_setitem(container: DependencyContainer):
    s = object()
    container['service'] = s

    assert s is container['service']
    assert repr(s) in repr(container)


def test_update(container: DependencyContainer):
    container[Service] = Service()

    another_service = AnotherService()
    x = object()

    container.update({
        Service: another_service,
        'x': x
    })

    assert another_service is container[Service]
    assert x is container['x']


def test_extend(container: DependencyContainer):
    provider = DummyProvider()
    container.providers[DummyProvider] = provider

    # Can't check directly if the container is the same, as a proxy is used
    assert provider is container.providers[DummyProvider]


def test_getitem_and_provide(container: DependencyContainer):
    container.providers[DummyFactoryProvider] = DummyFactoryProvider({
        Service: lambda: Service(),
        ServiceWithNonMetDependency: lambda: ServiceWithNonMetDependency(),
    })
    container.providers[DummyProvider] = DummyProvider({'name': 'Antidote'})

    for get in (container.__getitem__, container.provide):
        with pytest.raises(DependencyNotFoundError):
            get(object)

        with pytest.raises(DependencyInstantiationError):
            get(ServiceWithNonMetDependency)

    assert isinstance(container[Service], Service)
    assert isinstance(container[Dependency(Service)], Service)
    assert isinstance(container.provide(Service), Service)
    assert 'Antidote' == container['name']
    assert 'Antidote' == container[Dependency('name')]
    assert 'Antidote' == container.provide('name')


def test_singleton(container: DependencyContainer):
    container.providers[DummyFactoryProvider] = DummyFactoryProvider({
        Service: lambda: Service(),
        AnotherService: lambda: AnotherService(),
    })

    service = container[Service]
    container.providers[DummyFactoryProvider][Service] = lambda: object()
    assert service is container[Service]

    container.providers[DummyFactoryProvider].create_singleton = False
    another_service = container[AnotherService]
    assert another_service is not container[AnotherService]


def test_cycle_error(container: DependencyContainer):
    container.providers[DummyFactoryProvider] = DummyFactoryProvider({
        Service: lambda: Service(container[AnotherService]),
        AnotherService: lambda: AnotherService(container[YetAnotherService]),
        YetAnotherService: lambda: YetAnotherService(container[Service]),
    })

    with pytest.raises(DependencyCycleError):
        container[Service]

    with pytest.raises(DependencyCycleError):
        container[AnotherService]

    with pytest.raises(DependencyCycleError):
        container[YetAnotherService]


def test_repr_str(container: DependencyContainer):
    container.providers[DummyProvider] = DummyProvider({'name': 'Antidote'})
    container['test'] = 1

    assert 'test' in repr(container)
    assert repr(container.providers[DummyProvider]) in repr(container)
    assert str(container.providers[DummyProvider]) in str(container)


def test_context_isolation(container: DependencyContainer):
    container['test'] = 1
    container['name'] = 'Antidote'
    s = Service()
    container[Service] = s

    with container.context():
        assert s is container[Service]
        assert 1 == container['test']
        assert 'Antidote' == container['name']

        container['another_service'] = AnotherService()
        assert isinstance(container['another_service'], AnotherService)

        s2 = Service()
        container[Service] = s2
        assert s2 is container[Service]

    with pytest.raises(DependencyNotFoundError):
        container['another_service']

    assert s is container[Service]
    assert 1 == container['test']
    assert 'Antidote' == container['name']


def test_context_include(container: DependencyContainer):
    container['test'] = 1
    container['name'] = 'Antidote'
    s = Service()
    container[Service] = s

    with container.context(include=[Service]):
        assert s is container[Service]

        with pytest.raises(DependencyNotFoundError):
            container['name']

        with pytest.raises(DependencyNotFoundError):
            container['test']

    with container.context(include=[]):
        with pytest.raises(DependencyNotFoundError):
            container[Service]

        with pytest.raises(DependencyNotFoundError):
            container['name']

        with pytest.raises(DependencyNotFoundError):
            container['test']


def test_context_exclude(container: DependencyContainer):
    container['test'] = 1
    container['name'] = 'Antidote'
    s = Service()
    container[Service] = s

    with container.context(exclude=['name']):
        assert s is container[Service]
        assert 1 == container['test']

        with pytest.raises(DependencyNotFoundError):
            container['name']


def test_context_override(container: DependencyContainer):
    container['test'] = 1
    container['name'] = 'Antidote'
    s = Service()
    container[Service] = s

    with container.context(dependencies=dict(test=2, name='testing')):
        assert s is container[Service]
        assert 2 == container['test']
        assert 'testing' == container['name']


def test_context_missing(container: DependencyContainer):
    container['test'] = 1
    container.providers[DummyProvider] = DummyProvider({'name': 'Antidote'})
    s = Service()
    container[Service] = s

    with container.context(missing=['name']):
        assert s is container[Service]
        assert 1 == container['test']

        with pytest.raises(DependencyNotFoundError):
            container['name']

    with container.context(missing=['test'], include=[Service]):
        assert s is container[Service]
        assert 'Antidote' == container['name']

        with pytest.raises(DependencyNotFoundError):
            container['test']
