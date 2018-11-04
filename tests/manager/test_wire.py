import pytest

from antidote import DependencyManager


def test_wire():
    manager = DependencyManager()
    container = manager.container

    class Service:
        pass

    class AnotherService:
        pass

    manager.register(Service)
    manager.register(AnotherService)

    @manager.wire(arg_map=dict(service=Service,
                               another_service=AnotherService))
    class Something:
        def f(self, service):
            return service

        def g(self, another_service):
            return another_service

        def h(self, service, another_service):
            return service, another_service

        def u(self):
            pass

        def v(self, nothing):
            return nothing

    something = Something()
    assert container[Service] is something.f()
    assert container[AnotherService] is something.g()

    s1, s2 = something.h()
    assert container[Service] is s1
    assert container[AnotherService] is s2

    something.u()

    with pytest.raises(TypeError):
        something.v()


def test_invalid_wire():
    manager = DependencyManager()

    with pytest.raises(ValueError):
        @manager.wire
        def f():
            pass
