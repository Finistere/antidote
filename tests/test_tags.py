from typing import cast

import pytest

from antidote import (Factory, factory, Service, Tag, Tagged,
                      world)


@pytest.fixture(autouse=True)
def new_world():
    with world.test.new():
        yield


tag = Tag()


class A:
    pass


class B:
    pass


def test_tags():
    @factory(tags=[tag])
    def build_a() -> A:
        return A()

    class BFactory(Factory):
        __antidote__ = Factory.Conf(tags=[tag])

        def __call__(self) -> B:
            return B()

    class X(Service):
        __antidote__ = Service.Conf(tags=[tag])

    tagged = cast(Tagged, world.get(tag))

    assert len(tagged) == 3
    assert list(tagged.tags()) == [tag, tag, tag]
    assert set(tagged.values()) == {world.get(A @ build_a),
                                    world.get(B @ BFactory),
                                    world.get(X)}


def test_multiple_tags():
    tag2 = Tag()
    tags = [tag, tag2]

    @factory(tags=tags)
    def build_a() -> A:
        return A()

    class BFactory(Factory):
        __antidote__ = Factory.Conf(tags=tags)

        def __call__(self) -> B:
            return B()

    class X(Service):
        __antidote__ = Service.Conf(tags=tags)

    for t in tags:
        tagged = cast(Tagged, world.get(t))
        assert len(tagged) == 3
        assert list(tagged.tags()) == [t, t, t]
        assert set(tagged.values()) == {world.get(A @ build_a),
                                        world.get(B @ BFactory),
                                        world.get(X)}


def test_custom_tags():
    class CustomTag(Tag):
        __slots__ = ('name', 'attr')
        name: str
        attr: int

        def __init__(self, name: str, attr: int = 0):
            super().__init__(name=name, attr=attr)

        def group(self):
            return self.name

    tag1 = CustomTag('my_tag', attr=1)

    @factory(tags=[tag1])
    def build_a() -> A:
        return A()

    tag2 = CustomTag('my_tag', attr=2)

    class BFactory(Factory):
        __antidote__ = Factory.Conf(tags=[tag2])

        def __call__(self) -> B:
            return B()

    tag3 = CustomTag('my_tag', attr=3)

    class X(Service):
        __antidote__ = Service.Conf(tags=[tag3])

    tagged = cast(Tagged, world.get(CustomTag('my_tag')))
    assert len(tagged) == 3
    assert set(tagged.items()) == {
        (tag1, world.get(A @ build_a)),
        (tag2, world.get(B @ BFactory)),
        (tag3, world.get(X))
    }
