import pytest
from hypothesis import given, strategies as st

from antidote import Tag, Tagged, world
from antidote.core import DependencyContainer, DependencyInstance
from antidote.core.exceptions import FrozenWorldError
from antidote.exceptions import DependencyNotFoundError, DuplicateTagError
from antidote.providers.tag import TaggedDependencies, TagProvider


class Service:
    pass


@pytest.fixture()
def provider():
    with world.test.empty():
        provider = TagProvider()
        world.get(DependencyContainer).register_provider(provider)
        yield provider


def test_tag():
    t = Tag(name='test', val='x')

    assert 'test' == t.name
    assert 'x' == t.val
    assert t.anything is None
    assert "val='x'" in repr(t)
    assert "'test'" in repr(t)
    assert "val='x'" in str(t)
    assert "'test'" in str(t)

    t2 = Tag(name='test')
    assert "'test'" in str(t2)


@pytest.mark.parametrize('name,error', [('', ValueError),
                                        (object(), TypeError)])
def test_invalid_tag(name, error):
    with pytest.raises(error):
        Tag(name)


@given(st.builds(Tagged, name=st.sampled_from(['test', '987 jkh@è'])))
def test_tagged_eq_hash(tagged):
    # does not fail
    hash(tagged)

    for f in (lambda e: e, hash):
        assert f(Tagged(tagged.name)) != f(tagged)

    assert repr(tagged.name) in repr(tagged)


@pytest.mark.parametrize('name,error', [('', ValueError), (object(), TypeError)])
def test_invalid_tagged(name, error):
    with pytest.raises(error):
        Tagged(name)


def test_tagged_dependencies():
    tag1 = Tag('tag1')
    tag2 = Tag('tag2', dummy=True)
    c = DependencyContainer()

    t = TaggedDependencies(
        container=c,
        dependencies=['d', 'd2'],
        tags=[tag1, tag2]
    )

    assert {tag1, tag2} == set(t.tags())
    assert {'d', 'd2'} == set(t.dependencies())
    assert 2 == len(t)
    # instantiation from container
    c.update_singletons({'d': 'test', 'd2': 'test2'})
    assert {'test', 'test2'} == set(t.instances())
    # from cache
    c.update_singletons({'d': 'different', 'd2': 'different2'})
    assert {'test', 'test2'} == set(t.instances())


def test_tagged_dependencies_invalid_dependency():
    tag = Tag('tag1')

    t = TaggedDependencies(
        container=world.get(DependencyContainer),
        dependencies=['d'],
        tags=[tag]
    )
    assert ['d'] == list(t.dependencies())
    assert [tag] == list(t.tags())
    with pytest.raises(DependencyNotFoundError):
        list(t.instances())


def test_repr(provider: TagProvider):
    x = object()
    provider.register(x, [Tag(name='tag')])

    assert str(x) in repr(provider)


def test_provide_tags(provider: TagProvider):
    world.singletons.update(dict(test=object(), test2=object()))
    custom_tag = Tag('tag2', error=True)
    provider.register('test', ['tag1', custom_tag])
    provider.register('test2', ['tag2'])

    result = provider.world_provide(Tagged('xxxxx'))
    assert isinstance(result, DependencyInstance)
    assert result.singleton is False
    assert 0 == len(result.instance)

    result = provider.world_provide(Tagged('tag1'))
    assert isinstance(result, DependencyInstance)
    assert result.singleton is False
    #
    tagged_dependencies: TaggedDependencies = result.instance
    assert 1 == len(tagged_dependencies)
    assert ['test'] == list(tagged_dependencies.dependencies())
    assert ['tag1'] == [tag.name for tag in tagged_dependencies.tags()]
    assert [world.get('test') == list(tagged_dependencies.instances())]

    result = provider.world_provide(Tagged('tag2'))
    assert isinstance(result, DependencyInstance)
    assert result.singleton is False

    tagged_dependencies: TaggedDependencies = result.instance
    assert 2 == len(tagged_dependencies)
    assert {'test', 'test2'} == set(tagged_dependencies.dependencies())
    tags = list(tagged_dependencies.tags())
    assert {'tag2', 'tag2'} == {tag.name for tag in tags}
    assert any(tag is custom_tag for tag in tags)
    instances = {world.get('test'), world.get('test2')}
    assert instances == set(tagged_dependencies.instances())


@pytest.mark.parametrize('tag', ['tag', Tag(name='tag')])
def test_duplicate_tag_error(provider: TagProvider, tag):
    provider.register('test', [Tag(name='tag')])
    with pytest.raises(DuplicateTagError):
        provider.register('test', tags=[tag])


def test_duplicate_tag_error_in_same_register(provider: TagProvider):
    with pytest.raises(DuplicateTagError):
        provider.register('test', tags=[Tag(name='tag'), 'tag'])


@pytest.mark.parametrize(
    'tags',
    [
        [object],
        [lambda _: False],
        ['test', object]
    ]
)
def test_invalid_register(provider: TagProvider, tags):
    with pytest.raises(ValueError):
        provider.register('test', tags)


def test_all_must_be_valid_for_tag(provider: TagProvider):
    with pytest.raises(ValueError):
        provider.register('test', ['1', '2', 3])
    assert len(provider.world_provide(Tagged('1')).instance) == 0


@pytest.mark.parametrize('dependency', ['test', Service, object()])
def test_unknown_dependency(provider: TagProvider, dependency):
    assert provider.world_provide(dependency) is None


def test_clone(provider: TagProvider):
    world.singletons.set('test', 'test')
    provider.register('test', ['tag'])
    cloned = provider.clone()

    tagged = cloned.world_provide(Tagged('tag')).instance
    assert len(tagged) == 1
    assert next(tagged.dependencies()) == 'test'

    cloned.register('test', ['tag2'])
    tagged = cloned.world_provide(Tagged('tag2')).instance
    assert len(tagged) == 1
    assert next(tagged.dependencies()) == 'test'

    assert len(provider.world_provide(Tagged('tag2')).instance) == 0


def test_freeze(provider: TagProvider):
    provider.freeze()

    with pytest.raises(FrozenWorldError):
        provider.register('test', ['tag'])
