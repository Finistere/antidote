import pytest

from antidote.core import DependencyContainer, DependencyInstance
from antidote.exceptions import DependencyNotFoundError, DuplicateTagError
from antidote.providers.tag import Tag, TagProvider, Tagged, TaggedDependencies


def test_repr():
    provider = TagProvider(DependencyContainer())

    x = object()
    provider.register(x, [Tag(name='tag')])

    assert str(x) in repr(provider)


def test_duplicate_tag_error():
    provider = TagProvider(DependencyContainer())

    provider.register('test', [Tag(name='tag')])
    with pytest.raises(DuplicateTagError):
        provider.register('test', ['tag'])

    with pytest.raises(DuplicateTagError):
        provider.register('test', [Tag(name='tag')])

    with pytest.raises(DuplicateTagError):
        provider.register('test2', [Tag(name='tag'), 'tag'])


def test_invalid_tag():
    provider = TagProvider(DependencyContainer())

    with pytest.raises(ValueError):
        provider.register('test', [object])

    with pytest.raises(ValueError):
        provider.register('test', [lambda _: False])


def test_provide_tags():
    container = DependencyContainer()
    container.update_singletons(dict(test=object(), test2=object()))
    provider = TagProvider(container)
    provider.register('test', ['tag1', Tag('tag2', error=True)])
    provider.register('test2', ['tag2'])

    result = provider.provide(Tagged('xxxxx'))
    assert isinstance(result, DependencyInstance)
    assert result.singleton is False
    assert 0 == len(result.instance)

    result = provider.provide(Tagged('tag1'))
    assert isinstance(result, DependencyInstance)
    assert result.singleton is False
    #
    tagged_dependencies = result.instance  # type: TaggedDependencies
    assert 1 == len(tagged_dependencies)
    assert ['test'] == list(tagged_dependencies.dependencies())
    assert ['tag1'] == [tag.name for tag in tagged_dependencies.tags()]
    assert [container['test']] == list(tagged_dependencies.instances())

    result = provider.provide(Tagged('tag2'))
    assert isinstance(result, DependencyInstance)
    assert result.singleton is False

    tagged_dependencies = result.instance  # type: TaggedDependencies
    assert 2 == len(tagged_dependencies)
    assert ['test', 'test2'] == list(tagged_dependencies.dependencies())
    tags = list(tagged_dependencies.tags())
    assert ['tag2', 'tag2'] == [tag.name for tag in tags]
    assert tags[0].error
    instances = [container['test'], container['test2']]
    assert instances == list(tagged_dependencies.instances())


def test_tagged_dependencies():
    tag1 = Tag('tag1')
    tag2 = Tag('tag2', dummy=True)
    c = DependencyContainer()
    c.update_singletons({'d': 'test', 'd2': 'test2'})

    t = TaggedDependencies(
        container=c,
        dependencies=['d', 'd2'],
        tags=[tag1, tag2]
    )

    assert {tag1, tag2} == set(t.tags())
    assert {'test', 'test2'} == set(t.instances())
    assert {'d', 'd2'} == set(t.dependencies())
    assert 2 == len(t)


def test_tagged_dependencies_invalid_dependency():
    tag = Tag('tag1')
    c = DependencyContainer()

    t = TaggedDependencies(
        container=c,
        dependencies=['d'],
        tags=[tag]
    )
    assert ['d'] == list(t.dependencies())
    assert [tag] == list(t.tags())
    with pytest.raises(DependencyNotFoundError):
        list(t.instances())
