from antidote import DependencyManager


def test_inject():
    manager = DependencyManager()
    container = manager.container

    class Service:
        pass

    manager.register(Service)

    @manager.inject
    def f(service: Service):
        return service

    assert container[Service] is f()


def test_register():
    manager = DependencyManager()
    container = manager.container

    @manager.register
    class Service:
        pass

    assert isinstance(container[Service], Service)

    @manager.register
    class AnotherService:
        def __init__(self, service: Service):
            self.service = service

    assert isinstance(container[AnotherService], AnotherService)
    assert isinstance(container[AnotherService].service, Service)


def test_provider_function():
    manager = DependencyManager()
    container = manager.container

    @manager.register
    class Service:
        pass

    class AnotherService:
        def __init__(self, service):
            self.service = service

    @manager.factory
    def provider(service: Service) -> AnotherService:
        return AnotherService(service)

    assert isinstance(container[AnotherService], AnotherService)
    assert isinstance(container[AnotherService].service, Service)


def test_provider_class():
    manager = DependencyManager()
    container = manager.container

    @manager.register
    class Service:
        pass

    class AnotherService:
        def __init__(self, service):
            self.service = service

    @manager.factory
    class Provider:
        def __call__(self, service: Service) -> AnotherService:
            return AnotherService(service)

    assert isinstance(container[AnotherService], AnotherService)
    assert isinstance(container[AnotherService].service, Service)
