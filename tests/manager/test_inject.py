import pytest

from antidote import DependencyManager


def test_inject_bind():
    manager = DependencyManager()
    container = manager.container

    class Service:
        pass

    manager.register(Service)

    @manager.inject(bind=True)
    def f(x):
        return x

    with pytest.raises(TypeError):
        f()

    @manager.inject(arg_map=dict(x=Service), bind=True)
    def g(x):
        return x

    assert container[Service] is g()

    # arguments are bound, so one should not be able to pass injected
    # argument.
    with pytest.raises(TypeError):
        g(1)

    container['service'] = container[Service]
    container['service_bis'] = container[Service]

    @manager.inject(use_names=True, bind=True)
    def h(service, service_bis=None):
        return service, service_bis

    result = h()
    assert container[Service] is result[0]
    assert container[Service] is result[1]

    @manager.inject(use_names=('service',), bind=True)
    def h(service, service_bis=None):
        return service, service_bis

    result = h()
    assert container[Service] is result[0]
    assert None is result[1]


def test_inject_with_mapping():
    manager = DependencyManager()
    container = manager.container

    class Service:
        pass

    manager.register(Service)

    class AnotherService:
        pass

    manager.register(AnotherService)

    @manager.inject
    def f(x):
        return x

    with pytest.raises(TypeError):
        f()

    @manager.inject(arg_map=dict(x=Service))
    def g(x):
        return x

    assert container[Service] is g()

    @manager.inject(arg_map=(Service,))
    def g(x):
        return x

    assert container[Service] is g()

    @manager.inject(arg_map=dict(x=Service))
    def h(x, b=1):
        return x

    assert container[Service] is h()

    @manager.inject(arg_map=(Service,))
    def h(x, b=1):
        return x

    assert container[Service] is h()

    manager.arg_map = dict(x=Service, y=AnotherService)

    @manager.inject
    def u(x, y):
        return x, y

    assert container[Service] is u()[0]
    assert container[AnotherService] is u()[1]

    @manager.inject(arg_map=dict(y=Service))
    def v(x, y):
        return x, y

    assert container[Service] is v()[0]
    assert container[Service] is v()[1]

    @manager.inject(arg_map=(AnotherService,))
    def v(x, y):
        return x, y

    assert container[AnotherService] is v()[0]
    assert container[AnotherService] is v()[1]


def test_use_names():
    manager = DependencyManager(use_names=False)
    container = manager.container

    _service = object()
    _service_bis = object()
    container['service'] = _service
    container['service_bis'] = _service_bis

    def f(service):
        return service

    with pytest.raises(TypeError):
        manager.inject(f)()

    def g(service, service_bis=None, something=None):
        return service, service_bis, something

    g_result = manager.inject(use_names=True)(g)()
    assert _service is g_result[0]
    assert _service_bis is g_result[1]
    assert None is g_result[2]

    g_result = manager.inject(use_names=('service',))(g)()
    assert _service is g_result[0]
    assert None is g_result[1]
    assert None is g_result[2]

    # use names for every injection by default.
    manager.use_names = True

    assert _service is manager.inject(f)()

    with pytest.raises(TypeError):
        manager.inject(use_names=False)(f)()
