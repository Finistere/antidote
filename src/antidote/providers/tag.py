from __future__ import annotations

import threading
from typing import (Any, Dict, final, Generic, Hashable, Iterable, Iterator, List,
                    Optional, Tuple, TypeVar)

from .._internal import API
from .._internal.utils import FinalMeta
from ..core import DependencyContainer, DependencyInstance, DependencyProvider
from ..core.exceptions import AntidoteError


@API.public
class Tag:
    """
    Tags are a way to expose a dependency indirectly. Instead of explicitly
    defining a list of dependencies to retrieve, one can just mark those with
    tags and retrieve them.

    The only requirement for a tag is to be an instance of :py:class:`.Tag`.

    .. doctest::

        >>> from antidote import Tag, Service, world
        >>> tag = Tag()
        >>> class Dummy(Service):
        ...     __antidote__ = Service.Conf(tags=[tag])
        >>> world.get(tag)
        TaggedDependencies
        >>> # You can retrieve the tags and/or dependencies. Here we take both.
        ... (t, dummy) = list(world.get(tag).items())[0]
        >>> t is tag
        True
        >>> dummy is world.get(Dummy)
        True

    You may create your own subclasses to add additional information on your services.
    You can create Tags will be grouped by the output of :py:meth:`.group`. Retrieved
    dependencies will have their associated tag provided, so you can store information
    in it.

    .. doctest::

        >>> from antidote import Tag, Service, world
        >>> class CustomTag(Tag):
        ...     __slots__ = ('name',)  # __slots__ isn't necessary
        ...     name: str  # For Mypy
        ...
        ...     def __init__(self, name: str):
        ...         super().__init__(name=name)
        ...
        ...     def group(self):
        ...         return self.name.split("_")[0]
        ...
        >>> class Dummy(Service):
        ...     __antidote__ = Service.Conf(tags=[CustomTag(name="ref_dummy")])
        >>> world.get[TaggedDependencies[CustomTag, object]](CustomTag("ref_any"))
        TaggedDependencies
        >>> (tag, dummy) = list(world.get(tag).items())[0]
        >>> tag.name
        ref_dummy
        >>> dummy is world.get(Dummy)
        True

    Note that tags are immutables, well as far it goes in Python ! Tags should be used to
    group dependencies and eventually provides some *constants* information on them. It
    is not intended to store any state in it.

    """
    __slots__ = ()

    def __init__(self, **attrs):
        """
        :py:meth:`.__init__` is the only way to actually set attributes, to be used by
        subclasses.
        """
        for attr, value in attrs.items():
            object.__setattr__(self, attr, value)

    @final
    def __setattr__(self, name, value):
        raise AttributeError(f"{type(self)} is immutable")

    def group(self):
        """Tags will be grouped by this value. By default it's the tag instance itself."""
        return self


@API.public
class DuplicateTagError(AntidoteError):
    """
    A dependency has multiple times the same tag.
    """

    def __init__(self, dependency: Hashable, existing_tag: Tag):
        self.dependency = dependency
        self.existing_tag = existing_tag

    def __str__(self):
        return f"Dependency {self.dependency} already has a tag {self.existing_tag}" \
               f"with id={self.existing_tag.group()}"


T = TypeVar('T', bound=Tag)
D = TypeVar('D')


@API.public
@final
class TaggedDependencies(Generic[T, D], metaclass=FinalMeta):
    """
    Collection containing dependencies and their tags. Dependencies are lazily
    instantiated.
    """

    @API.private  # You're not supposed to create it yourself
    def __init__(self,
                 container: DependencyContainer,
                 dependencies: List[Hashable],
                 tags: List[T]):
        self.__lock = threading.RLock()
        self.__container = container
        self.__dependencies = list(dependencies)
        self._instances: List[Any] = []
        self._tags = list(tags)

    def __len__(self):
        return len(self._tags)

    def items(self) -> Iterator[Tuple[T, D]]:
        """
        Zips tags and values together.
        """
        return zip(self.tags(), self.values())

    # Mainly here for interface consistency with instances() (instead of _tags)
    def tags(self) -> Iterator[T]:
        """Tags associated with the retrieved dependencies."""
        return iter(self._tags)

    def values(self) -> Iterator[D]:
        """Retrieved dependencies, lazily instantiated."""
        i = -1
        for i, instance in enumerate(self._instances):
            yield instance

        i += 1
        while i < len(self):
            try:
                yield self._instances[i]
            except IndexError:
                with self.__lock:
                    # If not other thread has already added the instance.
                    if i == len(self._instances):
                        self._instances.append(
                            self.__container.get(self.__dependencies[i])
                        )
                yield self._instances[i]
            i += 1

        # Don't need to keep them anymore.
        self.__container = None
        self.__dependencies = None
        self.__lock = None


@API.private
class TagProvider(DependencyProvider):
    def __init__(self):
        super().__init__()
        self.__tag_to_dependencies: Dict[Any, Dict[Hashable, Tag]] = {}

    def __repr__(self):
        return f"{type(self).__name__}(tagged_dependencies={self.__tag_to_dependencies})"

    def clone(self, keep_singletons_cache: bool) -> TagProvider:
        p = TagProvider()
        p.__tag_to_dependencies = self.__tag_to_dependencies.copy()
        return p

    def provide(self, dependency: Hashable, container: DependencyContainer
                ) -> Optional[DependencyInstance]:
        if isinstance(dependency, Tag):
            try:
                tag_and_dependencies = self.__tag_to_dependencies[dependency.group()]
            except KeyError:
                dependencies, tags = [], []
            else:
                dependencies, tags = zip(*tag_and_dependencies.items())

            return DependencyInstance(
                TaggedDependencies(
                    container=container,
                    dependencies=dependencies,
                    tags=tags
                ),
                # Whether the returned dependencies are singletons or not is
                # our decision to take.
                singleton=False
            )

        return None

    def register(self, dependency: Hashable, *, tags: Iterable[Tag]):
        tags = list(tags)
        for tag in tags:
            if not isinstance(tag, Tag):
                raise TypeError(f"Expecting tag of type Tag, not {type(tag)}")

        for tag in tags:
            key = tag.group()
            if key not in self.__tag_to_dependencies:
                self.__tag_to_dependencies[key] = {dependency: tag}
            elif dependency not in self.__tag_to_dependencies[key]:
                self.__tag_to_dependencies[key][dependency] = tag
            else:
                raise DuplicateTagError(dependency,
                                        self.__tag_to_dependencies[key][dependency])
