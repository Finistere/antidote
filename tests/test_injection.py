import pytest

from antidote import (DependencyInstantiationError, DependencyNotProvidableError,
                      Provider)
from antidote.helpers import factory, getter, new_container, provider, register
from antidote.injection import inject, wire


class Service:
    pass


class AnotherService:
    pass


class YetAnotherService:
    pass


class SuperService:
    pass


@pytest.fixture()
def container():
    c = new_container()

    c.update({cls: cls() for cls in [Service, AnotherService, YetAnotherService]})
    c.update(dict(service=object(),
                  another_service=object()))

    return c


class DummyMethodMixin:
    def method(self, yet_another_service: YetAnotherService):
        return yet_another_service


class MyService(DummyMethodMixin):
    def __init__(self,
                 service: Service,
                 another_service=None):
        self.service = service
        self.another_service = another_service


class F1(DummyMethodMixin):
    def __init__(self,
                 service: Service,
                 another_service=None):
        self.service = service
        self.another_service = another_service

    def __call__(self) -> MyService:
        return MyService(self.service, self.another_service)


class F2(DummyMethodMixin):
    def __init__(self, service: Service):
        self.service = service

    def __call__(self, another_service=None) -> MyService:
        return MyService(self.service, another_service)


class F3(DummyMethodMixin):
    def __call__(self,
                 service: Service,
                 another_service=None) -> MyService:
        return MyService(service, another_service)


class G1(DummyMethodMixin):
    def __init__(self,
                 service: Service,
                 another_service=None):
        self.service = service
        self.another_service = another_service

    def __call__(self, x) -> MyService:
        return MyService(self.service, self.another_service)


class G2(DummyMethodMixin):
    def __init__(self, service: Service):
        self.service = service

    def __call__(self, x, another_service=None) -> MyService:
        return MyService(self.service, another_service)


class G3(DummyMethodMixin):
    def __call__(self,
                 x,
                 service: Service,
                 another_service=None) -> MyService:
        return MyService(service, another_service)


class B1(DummyMethodMixin):
    def __init__(self, s, a):
        self.service = s
        self.another_service = a

    @classmethod
    def build(cls,
              service: Service,
              another_service=None):
        return cls(service, another_service)


class MyProvider(Provider, DummyMethodMixin):
    def __init__(self,
                 service: Service,
                 another_service=None):
        self.service = service
        self.another_service = another_service

    def provide(self, dependency):
        raise DependencyNotProvidableError(dependency)


def f1(service: Service, another_service=None) -> MyService:
    return MyService(service, another_service)


def g1(x, service: Service, another_service=None) -> MyService:
    return MyService(service, another_service)


def build(cls, service: Service, another_service=None):
    return cls(service, another_service)


def wire_(class_=None, auto_wire=True, **kwargs):
    if auto_wire is True:
        m = None
    elif auto_wire is False:
        m = []
    else:
        m = auto_wire

    return wire(class_=class_, methods=m, **kwargs)


wire_.__name__ = 'wire'


def getter_(func=None, **kwargs):
    return getter(func=func, namespace='my_service:', **kwargs)


getter_.__name__ = 'getter'


def register_build(class_=None, **kwargs):
    return register(class_, factory='build', **kwargs)


def register_external_build(class_=None, **kwargs):
    return register(class_, factory=build, **kwargs)


class_one_inj_tests = [
    [provider, MyProvider],
    [wire_, MyService],
    [register, MyService],
    [factory, F1],
    [factory, F3],
    [getter_, G1],
    [getter_, G3],
]

class_two_inj_tests = [
    [factory, F2],
    [getter_, G2],
]

class_tests = class_one_inj_tests + class_two_inj_tests

function_tests = [
    [factory, f1],
    [getter_, g1],
    [inject, f1],
    [register_build, B1],
    [register_external_build, B1],
]

all_tests = class_tests + function_tests


def parametrize_injection(tests, lazy=False, return_wrapped=False,
                          **inject_kwargs):
    def decorator(test):
        @pytest.mark.parametrize('wrapper,wrapped', tests)
        def f(container, wrapper, wrapped):
            original_wrapped = wrapped
            if isinstance(wrapped, type):
                # helpers do modify the class, so a copy has to be made to
                # avoid any conflict between the tests.
                wrapped = type(wrapped.__name__,
                               wrapped.__bases__,
                               wrapped.__dict__.copy())

            def create():
                name = wrapper.__name__
                inj_kwargs = inject_kwargs.copy()

                if ('getter' in name and original_wrapped is not G1) \
                        or 'register_external' in name:
                    try:
                        if isinstance(inj_kwargs['arg_map'], tuple):
                            inj_kwargs['arg_map'] = (
                                [None] + list(inj_kwargs['arg_map'])
                            )
                    except KeyError:
                        pass

                wrapped_ = wrapper(wrapped, container=container, **inj_kwargs)

                if return_wrapped:
                    if 'register' in name and 'build' in name:
                        try:
                            return container[wrapped_]
                        except DependencyInstantiationError as e:
                            raise TypeError() from e
                    else:
                        return wrapped_()

                if 'register' in name:
                    return container[wrapped_]
                elif 'factory' in name:
                    return container[MyService]
                elif 'getter' in name:
                    return container['my_service:*']
                elif 'provider' in name:
                    return container.providers[wrapped_]
                elif 'inject' in name or 'wire' in name:
                    return wrapped_()

            if lazy:
                return test(container,
                            create_instance=create)

            return test(container, instance=create())

        return f

    return decorator


@parametrize_injection(all_tests)
def test_basic_wiring(container, instance: MyService):
    assert instance.service is container[Service]
    assert instance.another_service is None


@parametrize_injection(class_tests, return_wrapped=True,
                       auto_wire=['__init__', 'method'])
def test_complex_wiring(container, instance: DummyMethodMixin):
    assert instance.method() is container[YetAnotherService]


@parametrize_injection(class_tests, lazy=True, return_wrapped=True,
                       auto_wire=False)
def test_no_wiring(container, create_instance):
    with pytest.raises(TypeError):
        instance = create_instance()
        if callable(instance):
            instance()


@parametrize_injection(all_tests, lazy=True, return_wrapped=True,
                       use_type_hints=False)
def test_no_type_hints(container, create_instance):
    with pytest.raises(TypeError):
        instance = create_instance()
        if callable(instance):
            instance()


@parametrize_injection(all_tests, use_type_hints=['service'])
def test_type_hints_only_service(container, instance):
    assert instance.service is container[Service]
    assert instance.another_service is None


@parametrize_injection(all_tests, lazy=True, return_wrapped=True,
                       use_type_hints=['another_service'])
def test_type_hints_only_another_service(container, create_instance):
    with pytest.raises(TypeError):
        instance = create_instance()
        if callable(instance):
            instance()


@parametrize_injection(all_tests,
                       arg_map=dict(service=AnotherService))
def test_arg_map_dict_override(container, instance: MyService):
    assert instance.service is container[AnotherService]
    assert instance.another_service is None


@parametrize_injection(all_tests,
                       arg_map=dict(another_service=AnotherService))
def test_arg_map_dict(container, instance: MyService):
    assert instance.service is container[Service]
    assert instance.another_service is container[AnotherService]


@parametrize_injection(class_one_inj_tests, arg_map=(None, AnotherService))
def test_class_arg_map_tuple_override(container, instance: MyService):
    assert instance.service is container[AnotherService]
    assert instance.another_service is None


@parametrize_injection(function_tests, arg_map=(AnotherService,))
def test_function_arg_map_tuple_override(container, instance: MyService):
    assert instance.service is container[AnotherService]
    assert instance.another_service is None


@parametrize_injection(class_one_inj_tests, arg_map=(None, None, AnotherService))
def test_class_arg_map_tuple(container, instance: MyService):
    assert instance.service is container[Service]
    assert instance.another_service is container[AnotherService]


@parametrize_injection(function_tests, arg_map=(None, AnotherService))
def test_function_arg_map_tuple(container, instance: MyService):
    assert instance.service is container[Service]
    assert instance.another_service is container[AnotherService]


@parametrize_injection(all_tests, use_names=True)
def test_use_names_activated(container, instance: MyService):
    assert instance.service is container[Service]
    assert instance.another_service is container['another_service']


@parametrize_injection(all_tests, use_names=['another_service'])
def test_use_names_only_another_service(container, instance: MyService):
    assert instance.service is container[Service]
    assert instance.another_service is container['another_service']


@parametrize_injection(all_tests, use_names=['service'])
def test_use_names_only_service(container, instance: MyService):
    assert instance.service is container[Service]
    assert instance.another_service is None
