# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
from typing import Any, Dict, Iterable, Iterator, List, Union

# @formatter:off
from cpython.dict cimport PyDict_GetItem
from cpython.ref cimport PyObject

from antidote._internal.lock cimport FastRLock
from antidote.core.container cimport (DependencyContainer, DependencyInstance,
                                      DependencyProvider)
# @formatter:on
from ..exceptions import DependencyNotFoundError, DuplicateTagError

cdef class Tag:
    def __init__(self, str name, **attrs):
        self.name = name
        self._attrs = attrs

    def __repr__(self):
        return "{}(name={!r}, **attrs={!r})".format(type(self).__name__,
                                                    self.name,
                                                    self._attrs)

    def __getattr__(self, item):
        return self._attrs.get(item)

cdef class Tagged:
    def __init__(self, str name):
        self.name = name

    def __repr__(self):
        return "{}(name={!r})".format(type(self).__name__, self.name)

cdef class TagProvider(DependencyProvider):
    """
    Provider managing string tag. Tags allows one to retrieve a collection of
    dependencies marked by their creator.
    """
    bound_dependency_types = (Tagged,)

    def __init__(self, DependencyContainer container):
        super().__init__(container)
        self._dependency_to_tag_by_tag_name = {}  # type: Dict[str, Dict[Any, Tag]]

    def __repr__(self):
        return "{}(tagged_dependencies={!r})".format(
            type(self).__name__,
            self._dependency_to_tag_by_tag_name
        )

    cpdef DependencyInstance provide(self, dependency):
        """
        Returns all dependencies matching the tag name specified with a
        :py:class:`~.dependency.Tagged`. For every other case, :obj:`None` is
        returned.

        Args:
            dependency: Only :py:class:`~.dependency.Tagged` is supported, all
                others are ignored.

        Returns:
            :py:class:`~.TaggedDependencies` wrapped in a
            :py:class:`~..core.Instance`.
        """
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
            ptr = PyDict_GetItem(self._dependency_to_tag_by_tag_name,
                                 tagged.name)

            if ptr != NULL:
                for dependency_, tag in (<dict> ptr).items():
                    dependencies.append(dependency_)
                    tags.append(tag)

            return DependencyInstance.__new__(
                DependencyInstance,
                TaggedDependencies.__new__(
                    TaggedDependencies,
                    container=self._container,
                    dependencies=dependencies,
                    tags=tags
                ),
                # Whether the returned dependencies are singletons or not is
                # their decision to take.
                singleton=False
            )

        return None

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
        for tag in tags:
            if isinstance(tag, str):
                tag = Tag(tag)

            if not isinstance(tag, Tag):
                raise ValueError("Expecting tag of type Tag, not {}".format(type(tag)))

            if tag.name not in self._dependency_to_tag_by_tag_name:
                self._dependency_to_tag_by_tag_name[tag.name] = {dependency: tag}
            elif dependency not in self._dependency_to_tag_by_tag_name[tag.name]:
                self._dependency_to_tag_by_tag_name[tag.name][dependency] = tag
            else:
                raise DuplicateTagError(tag.name)

cdef class TaggedDependencies:
    """
    Collection containing dependencies and their tags. Dependencies are lazily
    instantiated. This is thread-safe.

    Used by :py:class:`~.TagProvider` to return the dependencies matching a tag.
    """
    def __cinit__(self,
                  DependencyContainer container,
                  list dependencies,
                  list tags):
        self._lock = FastRLock()
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
            object instance

        while i < len(self):
            if i < n:
                yield self._instances[i]
            else:
                self._lock.acquire()
                try:
                    # If not other thread has already added the instance.
                    if i < len(self._instances):
                        instance = self._instances[i]
                    else:
                        instance = self._container.provide(self._dependencies[i])
                        if instance is self._container.SENTINEL:
                            raise DependencyNotFoundError(self._dependencies[i])

                        self._instances.append(instance)
                    n += 1
                finally:
                    self._lock.release()

                yield instance
            i += 1
