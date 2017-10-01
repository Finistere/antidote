from blood.container import *


def test_builder():
    container = ServiceContainer()
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


def test_register_with_annotations():
    manager = ServiceManager()

    @manager.register
    class Service(object):
        pass

    @manager.register
    class AnotherService(object):
        def __init__(self, service: Service):
            self.service = service

    assert isinstance(manager.container[AnotherService].service, Service)
