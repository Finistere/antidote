import threading
from collections import deque
from typing import Any, Callable, Dict, Generic, Iterable, Iterator, Tuple, TypeVar, \
    Union, List

from .base import Provider
from .._utils import SlotReprMixin
from ..container import Dependency, DependencyContainer, Instance
from ..exceptions import DependencyNotProvidableError, DuplicateTagError

T = TypeVar('T')


class Tag(SlotReprMixin):
    __slots__ = ('name', '_attrs')

    def __init__(self, name: str, **attrs):
        self.name = name
        self._attrs = attrs

    def __getattr__(self, item):
        return self._attrs.get(item)


class Tagged(Dependency):
    __slots__ = ('id', 'filter')

    def __init__(self, name: str, filter: Union[Callable[[Tag], bool]] = None):
        # If filter is None -> caching works.
        # If not, dependencies are still cached if necessary.
        super().__init__(name)
        if filter is not None and not callable(filter):
            raise ValueError("filter must be either a function or None")

        self.filter = filter or (lambda _: True)  # type: Callable[[Tag], bool]

    @property
    def name(self) -> str:
        return self.id

    def __hash__(self):
        return object.__hash__(self)

    def __eq__(self, other):
        return object.__eq__(self, other)


class TaggedDependencies(Generic[T]):
    def __init__(self, data: Iterable[Tuple[Callable[..., T], Tag]]):
        getters, self._tags = zip(*data)
        self._reverse_dependency_getters = deque(getters)
        self._dependency_instances = []  # type: List[T]
        self._lock = threading.Lock()

    def __iter__(self):
        return iter(self.dependencies())

    def __len__(self):
        return len(self._tags)

    def items(self) -> Iterable[Tuple[T, Tag]]:
        return zip(self.dependencies(), self.tags())

    def tags(self) -> Iterable[Tag]:
        return iter(self._tags)

    def dependencies(self) -> Iterator[T]:
        if self._reverse_dependency_getters:
            for i in range(len(self._tags)):
                try:
                    yield self._dependency_instances[i]
                except IndexError:
                    with self._lock:
                        try:
                            getter = self._reverse_dependency_getters.popleft()
                        except IndexError:
                            pass
                        else:
                            self._dependency_instances.append(getter())
                    yield self._dependency_instances[i]
        else:
            for dependency in self._dependency_instances:
                yield dependency


class TagProvider(Provider):
    def __init__(self, container: DependencyContainer):
        self._tagged_dependencies = {}  # type: Dict[str, Dict[Any, Tag]]
        self._container = container

    def __repr__(self):
        return "{}(tagged_dependencies={!r})".format(
            type(self).__name__,
            self._tagged_dependencies
        )

    def __antidote_provide__(self, dependency: Dependency) -> Instance:
        if isinstance(dependency, Tagged) \
                and dependency.name in self._tagged_dependencies:
            return Instance(
                TaggedDependencies((
                    ((lambda d=tagged_dependency: self._container[d]), tag)
                    for tagged_dependency, tag
                    in self._tagged_dependencies[dependency.name].items()
                    if dependency.filter(tag)
                )),
                # Tags are by nature dynamic. Whether the returned dependencies
                # are singletons or not is their decision to take.
                singleton=False
            )

        raise DependencyNotProvidableError(dependency)

    def register(self, dependency: Any, tags: Iterable[Union[str, Tag]]):
        for tag in tags:
            if isinstance(tag, str):
                tag = Tag(tag)

            if not isinstance(tag, Tag):
                raise ValueError("Expecting tags of type Tag, not {}".format(type(tag)))

            if tag.name not in self._tagged_dependencies:
                self._tagged_dependencies[tag.name] = {dependency: tag}
            elif dependency not in self._tagged_dependencies[tag.name]:
                self._tagged_dependencies[tag.name][dependency] = tag
            else:
                raise DuplicateTagError(tag.name)
