import pytest

from antidote import world
from antidote.core import DependencyInstance
from antidote.exceptions import DependencyNotFoundError, DuplicateTagError, \
    FrozenWorldError
from antidote.providers.tag import Tag, TaggedDependencies, TagProvider


class Service:
    pass


@pytest.fixture()
def provider():
    with world.test.empty():
        world.provider(TagProvider)
        yield world.get(TagProvider)


def test_tag():
    # id is unique
    assert Tag().group != Tag().group

    # Immutable
    with pytest.raises(AttributeError):
        Tag().x = 1


def test_repr(provider: TagProvider):
    class A:
        pass

    tag = Tag()
    provider.register(A, tags=[tag])

    assert str(tag) in repr(provider)
    assert str(A) in repr(provider)


def test_tagged_dependencies():
    with world.test.empty():
        world.singletons.update({
            'd': object(),
            'd2': object()
        })
        tag = Tag()

        from antidote._internal.state import get_container
        t = TaggedDependencies(
            container=get_container(),
            dependencies=['d', 'd2'],
            tags=[tag, tag]
        )

        assert set(t.tags()) == {tag}
        assert len(t) == 2

        expected = [world.get('d'), world.get('d2')]
        assert list(t.values()) == expected

        # tagged dependencies should only be retrieved once.
        with world.test.empty():
            world.singletons.update({
                'd': object(),
                'd2': object()
            })
            assert list(t.values()) == expected


def test_tagged_dependencies_invalid_dependency():
    with world.test.empty():
        tag = Tag()

        from antidote._internal.state import get_container
        t = TaggedDependencies(
            container=get_container(),
            dependencies=['d'],
            tags=[tag]
        )
        assert set(t.tags()) == {tag}
        assert len(t) == 1

        with pytest.raises(DependencyNotFoundError):
            list(t.values())


def test_provide_tags(provider: TagProvider):
    world.singletons.update(dict(test=object(), test2=object()))
    tagA = Tag()
    tagB = Tag()
    provider.register('test', tags=[tagA, tagB])
    provider.register('test2', tags=[tagB])

    # Unknown tag
    result = provider.test_provide(Tag())
    assert isinstance(result, DependencyInstance)
    assert result.singleton is False
    assert len(result.instance) == 0

    result = provider.test_provide(tagA)
    assert isinstance(result, DependencyInstance)
    assert result.singleton is False
    tagged_dependencies: TaggedDependencies = result.instance
    assert len(tagged_dependencies) == 1
    assert set(tagged_dependencies.tags()) == {tagA}
    assert {world.get('test')} == set(tagged_dependencies.values())

    result = provider.test_provide(tagB)
    assert isinstance(result, DependencyInstance)
    assert result.singleton is False
    tagged_dependencies: TaggedDependencies = result.instance
    assert len(tagged_dependencies) == 2
    assert {(tagB, world.get('test')),
            (tagB, world.get('test2'))} == set(tagged_dependencies.items())
    assert set(tagged_dependencies.tags()) == {tagB}
    assert {world.get('test'), world.get('test2')} == set(tagged_dependencies.values())


def test_custom_tags(provider: TagProvider):
    class CustomTag(Tag):
        __slots__ = ('name', 'attr')
        name: str
        attr: int

        def __init__(self, name: str, attr: int = 0):
            super().__init__(name=name, attr=attr)

        def group(self):
            return self.name

    world.singletons.update(dict(test=object(), test2=object()))
    test_tags = [CustomTag("A", attr=1), CustomTag("B", attr=1)]
    provider.register('test', tags=test_tags)
    test2_tags = [CustomTag("B", attr=2)]
    provider.register('test2', tags=test2_tags)

    result = provider.test_provide(CustomTag("A")).instance
    assert list(result.tags()) == [test_tags[0]]
    assert list(result.values()) == [world.get('test')]

    result = provider.test_provide(CustomTag("B")).instance
    if list(result.tags()) == [test_tags[1], test2_tags[0]]:
        assert list(result.values()) == [world.get('test'), world.get('test2')]
    elif list(result.tags()) == [test2_tags[0], test_tags[1]]:
        assert list(result.values()) == [world.get('test2'), world.get('test')]
    else:
        assert False


def test_duplicate_tag_error(provider: TagProvider):
    tag = Tag()

    with world.test.clone():
        provider = world.get(TagProvider)
        provider.register('test', tags=[tag])
        with pytest.raises(DuplicateTagError, match=f".*{tag}.*"):
            provider.register('test', tags=[tag])

    with world.test.clone():
        provider = world.get(TagProvider)
        with pytest.raises(DuplicateTagError, match=f".*{tag}.*"):
            provider.register('test', tags=[tag, tag])


@pytest.mark.parametrize(
    'tags',
    [
        [object],
        [lambda _: False],
        ['test', object],
    ]
)
def test_invalid_tags(provider: TagProvider, tags):
    with pytest.raises(TypeError):
        provider.register('test', tags=tags)


def test_all_must_be_valid_for_tag(provider: TagProvider):
    tag = Tag()
    with pytest.raises(TypeError):
        provider.register('test', tags=[tag, 3])
    assert len(provider.test_provide(tag).instance) == 0


@pytest.mark.parametrize('dependency', ['test', Service, object()])
def test_unknown_dependency(provider: TagProvider, dependency):
    assert provider.test_provide(dependency) is None


@pytest.mark.parametrize('keep_singletons_cache', [True, False])
def test_copy(provider: TagProvider,
              keep_singletons_cache: bool):
    world.singletons.update(dict(test=object(), test2=object(), test3=object()))
    tag = Tag()
    provider.register('test', tags=[tag])
    cloned = provider.clone(keep_singletons_cache)

    with pytest.raises(DuplicateTagError):
        cloned.register('test', tags=[tag])

    assert list(cloned.test_provide(tag).instance.tags()) == [tag]
    assert list(cloned.test_provide(tag).instance.values()) == [world.get('test')]

    tag2 = Tag()
    provider.register('test2', tags=[tag2])
    assert len(cloned.test_provide(tag2).instance) == 0

    tag3 = Tag()
    cloned.register('test3', tags=[tag3])
    assert len(provider.test_provide(tag3).instance) == 0


def test_freeze(provider: TagProvider):
    world.freeze()

    with pytest.raises(FrozenWorldError):
        provider.register("test", tags=[Tag()])
