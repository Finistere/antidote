import pytest
from antidote.exceptions import DuplicateTagError

from antidote.container import DependencyContainer, Instance

from antidote.providers.tags import TagProvider, Tag, TaggedDependencies, Tagged


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

    result = provider.__antidote_provide__(Tagged('tag1'))
    assert isinstance(result, Instance)
    assert result.singleton is False
    assert 1 == len(result.item)

    result = dict(result.item.items())
    assert result[container['test']].name == 'tag1'

    result = provider.__antidote_provide__(Tagged('tag2'))
    assert isinstance(result, Instance)
    assert result.singleton is False
    assert 2 == len(result.item)

    result = dict(result.item.items())
    assert 'tag2' == result[container['test2']].name
    assert 'tag2' == result[container['test']].name
    assert result[container['test']].error

    result = provider.__antidote_provide__(Tagged('tag2',
                                                  filter=lambda t: t.error is not True))
    assert isinstance(result, Instance)
    assert result.singleton is False
    assert 1 == len(result.item)

    result = dict(result.item.items())
    assert 'tag2' == result[container['test2']].name


def test_tagged_dependencies():
    data = {'test': Tag('tag1'), 'test2': Tag('tag2', dummy=True)}
    t = TaggedDependencies(data)

    assert set(data.values()) == set(t.tags())
    assert set(data.keys()) == set(t.dependencies())
    assert set(data.items()) == set(t.items())
    assert len(data) == len(t)
