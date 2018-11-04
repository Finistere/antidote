import pytest

from antidote import DependencyInstantiationError, DependencyManager


def test_register():
    manager = DependencyManager(auto_wire=True)
    container = manager.container

    @manager.register
    class Service:
        pass

    assert isinstance(container[Service], Service)

    @manager.register(arg_map=dict(service=Service))
    class AnotherService:
        def __init__(self, service):
            self.service = service

    assert isinstance(container[AnotherService], AnotherService)
    assert container[Service] is container[AnotherService].service
    # singleton
    assert container[AnotherService] is container[AnotherService]

    container['service'] = object()

    @manager.register(use_names=True)
    class YetAnotherService:
        def __init__(self, service):
            self.service = service

    assert isinstance(container[YetAnotherService], YetAnotherService)
    assert container['service'] is container[YetAnotherService].service
    # singleton
    assert container[YetAnotherService] is container[YetAnotherService]

    @manager.register(singleton=False)
    class SingleUsageService:
        pass

    assert isinstance(container[SingleUsageService], SingleUsageService)
    assert container[SingleUsageService] is not container[SingleUsageService]

    @manager.register(auto_wire=False)
    class BrokenService:
        def __init__(self, service):
            self.service = service

    with pytest.raises(DependencyInstantiationError):
        container[BrokenService]

    @manager.register(auto_wire=('__init__', 'method'),
                      arg_map=dict(service=Service,
                                   x=SingleUsageService,
                                   yet=YetAnotherService))
    class ComplexWiringService:
        def __init__(self, service):
            self.service = service

        def method(self, x, yet):
            return x, yet

    assert isinstance(container[ComplexWiringService], ComplexWiringService)
    assert container[Service] is container[ComplexWiringService].service
    output = container[ComplexWiringService].method()

    assert isinstance(output[0], SingleUsageService)
    assert output[1] is container[YetAnotherService]


def test_invalid_register():
    manager = DependencyManager()

    with pytest.raises(ValueError):
        manager.register(object())

    def f():
        pass

    with pytest.raises(ValueError):
        manager.register(f)
