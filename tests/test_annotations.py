from dependency_manager import Builder, Container, ServiceManager


def test_builder():
    container = Container()
    builder = Builder(container)

    class Service(object):
        pass

    container.register(Service, singleton=True)

    class Obj(object):
        def __init__(self, service: Service, parameter=2):
            self.service = service
            self.parameter = parameter

    s1 = builder.build(Obj)
    assert s1.service == container[Service]
    assert s1.parameter == 2

    s2 = builder.build(Obj, kwargs=dict(parameter=5))
    assert s2.service == container[Service]
    assert s2.parameter == 5


def test_inject():
    manager = ServiceManager()
    container = manager.container

    class Service(object):
        pass

    container.register(Service)

    @manager.inject
    def f(service: Service):
        return service

    assert container[Service] is f()


def test_register():
    manager = ServiceManager()
    container = manager.container

    @manager.register
    class Service(object):
        pass

    assert isinstance(container[Service], Service)

    @manager.register
    class AnotherService(object):
        def __init__(self, service: Service):
            self.service = service

    assert isinstance(container[AnotherService], AnotherService)
    assert isinstance(container[AnotherService].service, Service)


def test_provider_function():
    manager = ServiceManager()
    container = manager.container

    @manager.register
    class Service(object):
        pass

    class AnotherService(object):
        def __init__(self, service):
            self.service = service

    @manager.provider
    def provider(service: Service) -> AnotherService:
        return AnotherService(service)

    assert isinstance(container[AnotherService], AnotherService)
    assert isinstance(container[AnotherService].service, Service)


def test_provider_class():
    manager = ServiceManager()
    container = manager.container

    @manager.register
    class Service(object):
        pass

    class AnotherService(object):
        def __init__(self, service):
            self.service = service

    @manager.provider
    class Provider(object):
        def __call__(self, service: Service) -> AnotherService:
            return AnotherService(service)

    assert isinstance(container[AnotherService], AnotherService)
    assert isinstance(container[AnotherService].service, Service)
