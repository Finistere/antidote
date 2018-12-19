import pytest

from antidote.container import DependencyContainer, Instance
from antidote.exceptions import DuplicateTagError
from antidote.providers.tags import Tag, TagProvider, Tagged, TaggedDependencies


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
    container.update(dict(test=object(), test2=object()))
    provider = TagProvider(container)
    provider.register('test', ['tag1', Tag('tag2', error=True)])
    provider.register('test2', ['tag2'])

    result = provider.provide(Tagged('xxxxx'))
    assert isinstance(result, Instance)
    assert result.singleton is False
    assert 0 == len(result.item)

    result = provider.provide(Tagged('tag1'))
    assert isinstance(result, Instance)
    assert result.singleton is False
    assert 1 == len(result.item)

    result = dict(result.item.items())
    assert 'tag1' == result[container['test']].name

    result = provider.provide(Tagged('tag2'))
    assert isinstance(result, Instance)
    assert result.singleton is False
    assert 2 == len(result.item)

    result = dict(result.item.items())
    assert 'tag2' == result[container['test2']].name
    assert 'tag2' == result[container['test']].name
    assert result[container['test']].error

    result = provider.provide(Tagged('tag2',
                                     filter=lambda t: t.error is not True))
    assert isinstance(result, Instance)
    assert result.singleton is False
    assert 1 == len(result.item)

    result = dict(result.item.items())
    assert 'tag2' == result[container['test2']].name


def test_tagged_dependencies():
    tag1 = Tag('tag1')
    tag2 = Tag('tag2', dummy=True)
    t = TaggedDependencies(
        getter_tag_pairs=[
            (lambda: 'test', tag1),
            (lambda: 'test2', tag2)
        ]
    )

    assert {tag1, tag2} == set(t.tags())
    assert {'test', 'test2'} == set(t.dependencies())
    assert {'test', 'test2'} == set(t)
    assert {('test', tag1), ('test2', tag2)} == set(t.items())
    assert 2 == len(t)
