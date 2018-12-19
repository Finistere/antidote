import pytest

from antidote import Tag, Tagged
from antidote.helpers import factory, getter, new_container, register


class Service:
    pass


class AnotherService:
    pass


class ServiceFactory:
    def __call__(self) -> Service:
        return Service()


def service_factory() -> Service:
    return Service()


def conf(key):
    return dict(test=object())[key]


@pytest.fixture()
def container():
    return new_container()


tag_tests = [
    [register, Service],
    [factory, ServiceFactory],
    [factory, service_factory],
]

singleton_tests = tag_tests + [
    [getter, conf]
]


def parametrize_registration(tests, **kwargs):
    def decorator(test):
        @pytest.mark.parametrize('wrapper,wrapped', tests)
        def f(container, wrapper, wrapped):
            if isinstance(wrapped, type):
                # helpers do modify the class, so a copy has to be made to
                # avoid any conflict between the tests.
                wrapped = type(wrapped.__name__,
                               wrapped.__bases__,
                               wrapped.__dict__.copy())
            wrapped = wrapper(container=container, **kwargs)(wrapped)

            if wrapper == register:
                dependency_id = wrapped
            elif wrapper == getter:
                dependency_id = 'conf:test'
            else:
                dependency_id = Service

            return test(container, dependency_id=dependency_id)

        return f

    return decorator


@parametrize_registration(tag_tests, tags=[Tag('test')])
def test_single_tag(container, dependency_id):
    tagged = list(container[Tagged('test')])

    assert 1 == len(tagged)
    assert container[dependency_id] is tagged[0]


@parametrize_registration(tag_tests, tags=[Tag('test'), Tag('test2')])
def test_multi_tags(container, dependency_id):
    tagged = list(container[Tagged('test')])

    assert 1 == len(tagged)
    assert container[dependency_id] is tagged[0]

    tagged = list(container[Tagged('test2')])

    assert 1 == len(tagged)
    assert container[dependency_id] is tagged[0]


@parametrize_registration(singleton_tests, singleton=True)
def test_singleton(container, dependency_id):
    assert container[dependency_id] is container[dependency_id]


@parametrize_registration(singleton_tests, singleton=False)
def test_not_singleton(container, dependency_id):
    assert container[dependency_id] is not container[dependency_id]
