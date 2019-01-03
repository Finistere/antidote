import pytest

from antidote import factory, new_container, register, Tag, Tagged, TaggedDependencies


@pytest.fixture()
def container():
    return new_container()


def register_tag(container, tags):
    @register(container=container, tags=tags)
    class Service:
        pass

    return Service


def factory_tag(container, tags):
    class Service:
        pass

    @factory(container=container, tags=tags)
    def f() -> Service:
        pass

    return Service


@pytest.mark.parametrize(
    'func',
    [
        register_tag,
        factory_tag
    ]
)
def test_tags(container, func):
    tag = Tag('test')

    dependency = func(container, tags=[tag, 'dummy'])

    for tag_name in ['test', 'dummy']:
        tagged_dependencies = container[Tagged(tag_name)]  # type: TaggedDependencies
        assert 1 == len(tagged_dependencies)
        assert [container[dependency]] == list(tagged_dependencies.instances())
        assert [dependency] == list(tagged_dependencies.dependencies())

    tagged_dependencies = container[Tagged(tag.name)]  # type: TaggedDependencies
    assert [tag] == list(tagged_dependencies.tags())
