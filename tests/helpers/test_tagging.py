import itertools

import pytest

from antidote import factory, new_container, register, Tag, Tagged, TaggedDependencies


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


def parametrize_tagging(tags):
    def decorator(test):
        @pytest.mark.parametrize(
            'wrapper,wrapped,tags',
            [
                pytest.param(wrapper, wrapped, tags_,
                             id="{}-{}-{}".format(
                                 wrapper.__name__,
                                 wrapped.__name__,
                                 "+".join(map(str, tags_))
                             ))
                for (wrapper, wrapped), tags_
                in itertools.product(tag_tests, tags)
            ]

        )
        def f(container, wrapper, wrapped, tags):
            if isinstance(wrapped, type):
                # helpers do modify the class, so a copy has to be made to
                # avoid any conflict between the tests.
                wrapped = type(wrapped.__name__,
                               wrapped.__bases__,
                               wrapped.__dict__.copy())
            wrapped = wrapper(container=container, tags=tags)(wrapped)

            if wrapper == register:
                dependency = wrapped
            else:
                dependency = Service

            return test(container, dependency=dependency, tags=tags)

        return f

    return decorator


@parametrize_tagging([
    [Tag('test')],
    [Tag('test'), Tag('test2')],
    [Tag('test'), 'test2'],
    ['test'],
])
def test_multi_tags(container, dependency, tags):
    for tag in tags:
        tag_name = tag if isinstance(tag, str) else tag.name
        tagged_dependencies = container.get(
            Tagged(tag_name))  # type: TaggedDependencies  # noqa

        assert 1 == len(tagged_dependencies)
        assert [container.get(dependency) == list(tagged_dependencies.instances())]
        assert [dependency] == list(tagged_dependencies.dependencies())

        bound_tag, = list(tagged_dependencies.tags())
        if isinstance(tag, Tag):
            assert tag is bound_tag
        else:
            assert isinstance(bound_tag, Tag)
            assert tag_name == bound_tag.name
