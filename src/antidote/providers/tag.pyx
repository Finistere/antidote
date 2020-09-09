# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False
import threading
from typing import Any, Dict, Iterable, Iterator, List, Union

# @formatter:off
from cpython.dict cimport PyDict_GetItem
from cpython.ref cimport PyObject
from fastrlock.rlock cimport create_fastrlock, lock_fastrlock, unlock_fastrlock

from antidote.core.container cimport (DependencyContainer, DependencyInstance,
                                      DependencyProvider)
# @formatter:on
from ..core.exceptions import FrozenWorldError
from ..exceptions import DuplicateTagError

cdef class Tag:
    """
    Tags are a way to expose a dependency indirectly. Instead of explicitly
    defining a list of dependencies to retrieve, one can just mark those with
    tags and retrieve them. This helps decoupling dependencies, and may be used
    to add extensions to another service typically.

    The tag itself has a name (string) attribute, with which it is identified.
    One may add others attributes to pass additional information to the services
    retrieving it.

    .. doctest::

        >>> from antidote import Tag
        >>> t = Tag('dep', info=1)
        >>> t.info
        1

    """
    cdef:
        readonly str name
        readonly dict _attrs

    def __init__(self, str name: str, **attrs):
        """
        Args:
            name: Name which identifies the tag.
            **attrs: Any other parameters will be accessible as an attribute.
        """
        if len(name) == 0:
            raise ValueError("name must be a non empty string")

        self.name = name
        self._attrs = attrs

    def __repr__(self):
        return "{}(name={!r}, {})".format(
            type(self).__name__,
            self.name,
            ", ".join("{}={!r}".format(k, v) for k, v in self._attrs.items())
        )

    def __getattr__(self, item):
        return self._attrs.get(item)

cdef class Tagged:
    """
    Custom dependency used to retrieve all dependencies tagged with by with the
    name.
    """
    cdef:
        readonly str name

    def __init__(self, str name):
        """
        Args:
            name: Name of the tags which shall be retrieved.
        """
        if len(name) == 0:
            raise ValueError("name must be a non empty string")

        self.name = name

    def __repr__(self):
        return "{}(name={!r})".format(type(self).__name__, self.name)

cdef class TagProvider(DependencyProvider):
    """
    Provider managing string tag. Tags allows one to retrieve a collection of
    dependencies marked by their creator.
    """
    cdef:
        dict __dependency_to_tag_by_tag_name
        object __freeze_lock
        bint __frozen

    def __init__(self):
        self.__dependency_to_tag_by_tag_name = {}  # type: Dict[str, Dict[Any, Tag]]
        self.__freeze_lock = threading.RLock()
        self.__frozen = False

    def __repr__(self):
        return "{}(tagged_dependencies={!r})".format(
            type(self).__name__,
            self.__dependency_to_tag_by_tag_name
        )

    def freeze(self):
        with self.__freeze_lock:
            self.__frozen = True

    def clone(self):
        p = TagProvider()
        p.__dependency_to_tag_by_tag_name = self.__dependency_to_tag_by_tag_name.copy()
        return p

    cpdef DependencyInstance provide(self, dependency, DependencyContainer container):
        cdef:
            list dependencies
            list tags
            object dependency_
            Tagged tagged
            Tag tag
            PyObject*ptr

        if isinstance(dependency, Tagged):
            tagged = <Tagged> dependency
            dependencies = []
            tags = []
            ptr = PyDict_GetItem(self.__dependency_to_tag_by_tag_name,
                                 tagged.name)

            if ptr != NULL:
                for dependency_, tag in (<dict> ptr).items():
                    dependencies.append(dependency_)
                    tags.append(tag)

            return DependencyInstance.__new__(
                DependencyInstance,
                TaggedDependencies.__new__(
                    TaggedDependencies,
                    container=container,
                    dependencies=dependencies,
                    tags=tags
                ),
                # Whether the returned dependencies are singletons or not is
                # their decision to take.
                singleton=False
            )

    def register(self, dependency, tags: Iterable[Union[str, Tag]]):
        """
        Mark a dependency with all the supplied tags. Raises
        :py:exc:`~.exceptions.DuplicateTagError` if the tag has already been
        used for this dependency.

        Args:
            dependency: dependency to register.
            tags: Iterable of tags which should be associated with the
                dependency
        """
        tags = [Tag(t) if isinstance(t, str) else t for t in tags]
        for tag in tags:
            if not isinstance(tag, Tag):
                raise ValueError(f"Expecting tag of type Tag, not {type(tag)}")

        with self.__freeze_lock:
            if self.__frozen:
                raise FrozenWorldError(f"Cannot add tags {tags} to {dependency} "
                                       f"in a frozen world.")
            for tag in tags:
                if tag.name not in self.__dependency_to_tag_by_tag_name:
                    self.__dependency_to_tag_by_tag_name[tag.name] = {dependency: tag}
                elif dependency not in self.__dependency_to_tag_by_tag_name[tag.name]:
                    self.__dependency_to_tag_by_tag_name[tag.name][dependency] = tag
                else:
                    raise DuplicateTagError(tag.name)

cdef class TaggedDependencies:
    """
    Collection containing dependencies and their tags. Dependencies are lazily
    instantiated. This is thread-safe.

    Used by :py:class:`~.TagProvider` to return the dependencies matching a tag.
    """
    cdef:
        DependencyContainer _container
        object _lock
        list _dependencies
        list _tags
        list _instances

    def __cinit__(self,
                  DependencyContainer container,
                  list dependencies,
                  list tags):
        self._lock = create_fastrlock()
        self._container = container
        self._dependencies = dependencies  # type: List[Any]
        self._tags = tags  # type: List[Tag]
        self._instances = []  # type: List[Any]

    def __len__(self):
        return len(self._dependencies)

    def dependencies(self) -> Iterable[Any]:
        """
        Returns all the dependencies retrieved. This does not instantiate them.
        """
        return iter(self._dependencies)

    def tags(self) -> Iterable[Tag]:
        """
        Returns all the tags retrieved. This does not instantiate the
        dependencies.
        """
        return iter(self._tags)

    def instances(self) -> Iterator[Any]:
        """
        Returns the dependencies, in a stable order for multi-threaded
        environments.
        """
        cdef:
            ssize_t n = len(self._instances)
            ssize_t i = 0
            DependencyInstance dependency_instance
            object instance

        while i < len(self):
            if i < n:
                yield self._instances[i]
            else:
                lock_fastrlock(self._lock, -1, True)
                try:
                    # If not other thread has already added the instance.
                    if i < len(self._instances):
                        instance = self._instances[i]
                    else:
                        instance = self._container.get(self._dependencies[i])
                        self._instances.append(instance)
                    n += 1
                finally:
                    unlock_fastrlock(self._lock)

                yield instance
            i += 1
