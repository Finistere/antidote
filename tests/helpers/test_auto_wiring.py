import functools
from typing import Callable

import pytest

from antidote import (factory, inject, LazyConstantsMeta, new_container, provider,
                      register, wire)
from antidote.core import DependencyContainer, DependencyProvider
from antidote.exceptions import DependencyInstantiationError


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
    c.update_singletons({cls: cls() for cls in [Service, AnotherService,
                                                YetAnotherService]})
    c.update_singletons(dict(service=object(),
                             another_service=object()))
    return c


class MyService:
    def __init__(self,
                 service: Service,
                 another_service=None):
        self.service = service
        self.another_service = another_service

    def method(self, yet_another_service: YetAnotherService):
        return yet_another_service


class F1:
    def __init__(self,
                 service: Service,
                 another_service=None):
        self.service = service
        self.another_service = another_service

    def __call__(self) -> MyService:
        return MyService(self.service, self.another_service)

    def method(self, yet_another_service: YetAnotherService):
        return yet_another_service


class F2:
    def __init__(self, service: Service):
        self.service = service

    def __call__(self, another_service=None) -> MyService:
        return MyService(self.service, another_service)

    def method(self, yet_another_service: YetAnotherService):
        return yet_another_service


class F3:
    def __init__(self):
        pass

    def __call__(self,
                 service: Service,
                 another_service=None) -> MyService:
        return MyService(service, another_service)

    def method(self, yet_another_service: YetAnotherService):
        return yet_another_service


class B1:
    def __init__(self, s, a):
        self.service = s
        self.another_service = a

    @classmethod
    def build(cls,
              service: Service,
              another_service=None):
        return cls(service, another_service)

    def method(self, yet_another_service: YetAnotherService):
        return yet_another_service


class MyProvider(DependencyProvider):
    def __init__(self,
                 container: DependencyContainer,
                 service: Service,
                 another_service=None):
        self._container = container
        self.service = service
        self.another_service = another_service

    def provide(self, dependency):
        return

    def method(self, yet_another_service: YetAnotherService):
        return yet_another_service


def f1(service: Service, another_service=None) -> MyService:
    return MyService(service, another_service)


def g1(x, service: Service, another_service=None) -> MyService:
    return MyService(service, another_service)


def build(cls, service: Service, another_service=None):
    return cls(service, another_service)


def wire_(class_=None, auto_wire=True, **kwargs):
    if auto_wire is True:
        m = ['__init__']
    elif auto_wire is False:
        m = []
    else:
        m = auto_wire

    return wire(class_=class_, methods=m, **kwargs)


def resource(class_, **kwargs):
    return LazyConstantsMeta(
        'Resource' + class_.__name__,
        (),
        dict(
            __init__=class_.__init__,
            __call__=class_.__call__,
            method=class_.method
        ),
        lazy_method='__call__',
        **kwargs
    )


register_build = functools.partial(register, factory='build')
register_external_build = functools.partial(register, factory=build)

class_tests = [
    pytest.param(provider, MyProvider,
                 id='provider-MyProvider'),
    pytest.param(wire_, MyService,
                 id='wire-MyService'),
    pytest.param(register, MyService,
                 id='register-MyService'),
    pytest.param(factory, F1,
                 id='factory-F1'),
    pytest.param(factory, F2,
                 id='factory-F2'),
    pytest.param(factory, F3,
                 id='factory-F3'),
    pytest.param(register_build, B1,
                 id='register_build-B1'),
]

metaclass_tests = [
    pytest.param(resource, F1,
                 id='resource-F1'),
    pytest.param(resource, F2,
                 id='resource-F2'),
    pytest.param(resource, F3,
                 id='resource-F3')
]

function_tests = [
    pytest.param(factory, f1,
                 id='factory-f1'),
    pytest.param(inject, f1,
                 id='inject-f1'),
    pytest.param(register_external_build, B1,
                 id='register_external_build-B1'),
]

all_tests = metaclass_tests + class_tests + function_tests


def parametrize_injection(tests, lazy=False, return_wrapped=False,  # noqa: C901
                          create_subclass=False,
                          **inject_kwargs):
    def decorator(test):
        @pytest.mark.parametrize('wrapper,wrapped', tests)
        def f(container, wrapper, wrapped):
            if isinstance(wrapped, type):
                if create_subclass:
                    def __init__(*args, **kwargs):
                        pass

                    # Subclass to ensure wire_super is working properly.
                    wrapped = type("Sub" + wrapped.__name__,
                                   (wrapped,),
                                   {'__init__': __init__,
                                    'build': lambda cls: cls()})
                else:
                    # helpers do modify the class, so a copy has to be made to
                    # avoid any conflict between the tests.
                    wrapped = type(wrapped.__name__,
                                   wrapped.__bases__,
                                   wrapped.__dict__.copy())

            def create():
                inj_kwargs = inject_kwargs.copy()

                if wrapper == register_external_build:
                    try:
                        if isinstance(inj_kwargs['dependencies'], tuple):
                            # @formatter:off
                            inj_kwargs['dependencies'] = (
                                [None] + list(inj_kwargs['dependencies'])
                            )
                            # @formatter:on
                    except KeyError:
                        pass

                if wrapper == register_build:
                    try:
                        auto_wire = inj_kwargs['auto_wire']
                        if isinstance(auto_wire, list) and '__init__' in auto_wire:
                            auto_wire.append('build')
                            auto_wire.remove('__init__')
                    except KeyError:
                        pass

                wrapped_ = wrapper(wrapped, container=container, **inj_kwargs)

                if return_wrapped:
                    if wrapper in {register_build, register_external_build}:
                        try:
                            return container.get(wrapped_)
                        except DependencyInstantiationError as e:
                            raise TypeError() from e
                    else:
                        return wrapped_()

                if wrapper in {register, register_build, register_external_build}:
                    return container.get(wrapped_)
                elif wrapper == factory:
                    return container.get(MyService)
                elif wrapper == provider:
                    return container.providers[wrapped_]
                elif wrapper in {inject, wire_}:
                    return wrapped_()
                elif wrapper is resource:
                    return wrapped_()()
                else:
                    raise RuntimeError("Unsupported helper")

            if lazy:
                return test(container, create_instance=create)

            return test(container, instance=create())

        return f

    return decorator


@parametrize_injection(all_tests)
def test_basic_wiring(container, instance: MyService):
    assert instance.service is container.get(Service)
    assert instance.another_service is None


@parametrize_injection(metaclass_tests + class_tests, return_wrapped=True,
                       auto_wire=['__init__', 'method'])
def test_complex_wiring(container, instance: MyService):
    assert instance.method() is container.get(YetAnotherService)


@parametrize_injection(class_tests,
                       return_wrapped=True,
                       create_subclass=True,
                       auto_wire=['__init__', 'method'],
                       wire_super=True)
def test_subclass_wire_super(container, instance: MyService):
    assert instance.method() is container.get(YetAnotherService)


@parametrize_injection(class_tests,
                       lazy=True,
                       return_wrapped=True,
                       create_subclass=True,
                       auto_wire=['method'],
                       wire_super=False)
def test_subclass_no_wire_super(container, create_instance: Callable):
    with pytest.raises(TypeError):
        create_instance()


@parametrize_injection(all_tests, lazy=True, return_wrapped=True,
                       auto_wire=False)
def test_no_wiring(container, create_instance: Callable):
    with pytest.raises(TypeError):
        instance = create_instance()
        if callable(instance):
            instance()


@parametrize_injection(all_tests, lazy=True, return_wrapped=True,
                       use_type_hints=False)
def test_no_type_hints(container, create_instance: Callable):
    with pytest.raises(TypeError):
        instance = create_instance()
        if callable(instance):
            instance()


@parametrize_injection(all_tests, use_type_hints=['service'])
def test_type_hints_only_service(container, instance):
    assert instance.service is container.get(Service)
    assert instance.another_service is None


@parametrize_injection(all_tests, lazy=True, return_wrapped=True,
                       use_type_hints=['another_service'])
def test_type_hints_only_another_service(container, create_instance: Callable):
    with pytest.raises(TypeError):
        instance = create_instance()
        if callable(instance):
            instance()


@parametrize_injection(
    all_tests,
    dependencies=lambda s: AnotherService if s == 'service' else None
)
def test_dependencies_func_override(container, instance: MyService):
    assert instance.service is container.get(AnotherService)
    assert instance.another_service is None


@parametrize_injection(
    all_tests,
    dependencies=lambda s: AnotherService if s == 'another_service' else None
)
def test_dependencies_func(container, instance: MyService):
    assert instance.service is container.get(Service)
    assert instance.another_service is container.get(AnotherService)


@parametrize_injection(all_tests,
                       dependencies=dict(service=AnotherService))
def test_dependencies_dict_override(container, instance: MyService):
    assert instance.service is container.get(AnotherService)
    assert instance.another_service is None


@parametrize_injection(all_tests,
                       dependencies=dict(another_service=AnotherService))
def test_dependencies_dict(container, instance: MyService):
    assert instance.service is container.get(Service)
    assert instance.another_service is container.get(AnotherService)


@parametrize_injection(function_tests, dependencies=(AnotherService,))
def test_function_dependencies_tuple_override(container, instance: MyService):
    assert instance.service is container.get(AnotherService)
    assert instance.another_service is None


@parametrize_injection(function_tests, dependencies=(None, AnotherService))
def test_function_dependencies_tuple(container, instance: MyService):
    assert instance.service is container.get(Service)
    assert instance.another_service is container.get(AnotherService)


@parametrize_injection(all_tests, use_names=True)
def test_use_names_activated(container, instance: MyService):
    assert instance.service is container.get(Service)
    assert instance.another_service is container.get('another_service')


@parametrize_injection(all_tests, use_names=['another_service'])
def test_use_names_only_another_service(container, instance: MyService):
    assert instance.service is container.get(Service)
    assert instance.another_service is container.get('another_service')


@parametrize_injection(all_tests, use_names=['service'])
def test_use_names_only_service(container, instance: MyService):
    assert instance.service is container.get(Service)
    assert instance.another_service is None
