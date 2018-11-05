from typing import Callable, Dict, Generic, Iterable, Tuple, TypeVar, Union

from antidote._utils import SlotReprMixin
from ..container import Dependency, DependencyContainer, Instance
from ..exceptions import DependencyNotProvidableError, DuplicateTagError

T = TypeVar('T')


class Tag(SlotReprMixin):
    __slots__ = ('name', 'attrs')

    def __init__(self, name: str, **attrs):
        self.name = name
        self.attrs = attrs

    def __getattr__(self, item):
        try:
            return self.attrs[item]
        except KeyError:
            raise AttributeError(item)


class Tagged(Dependency):
    __slots__ = ('id', 'filter')

    def __init__(self, id: str, filter: Callable[[Tag], bool] = None):
        # If filter is None -> caching works.
        # If not, dependencies are still cached if necessary.
        super().__init__(id)
        self.filter = filter

    def __hash__(self):
        return hash((self.id, self.filter))

    def __eq__(self, other):
        return isinstance(other, Tagged) \
               and self.id == other.id \
               and self.filter == other.filter


class TaggedDependencies(Generic[T]):
    def __init__(self, data):
        self._data = data

    def tags(self) -> Iterable[Tag]:
        return self._data.values()

    def dependencies(self) -> Iterable[T]:
        return self._data.keys()

    def items(self) -> Iterable[Tuple[T, Tag]]:
        return self._data.items()


class TagProvider:
    def __init__(self, container: DependencyContainer):
        self._tagged_dependencies: Dict[str, Dict[Dependency, Tag]] = {}
        self._container = container

    def __repr__(self):
        return "{}(tagged_dependencies={!r})".format(
            type(self).__name__,
            self._tagged_dependencies
        )

    def __antidote_provide__(self, dependency: Dependency) -> Instance:
        if isinstance(dependency, Tagged):
            name = dependency.id  # type: str
            if name in self._tagged_dependencies:
                filter_ = dependency.filter or (lambda _: True)
                return Instance(
                    item=TaggedDependencies({
                        self._container[dependency]: tag
                        for dependency, tag in self._tagged_dependencies[name].items()
                        if filter_(tag)
                    }),
                    singleton=False
                )

        raise DependencyNotProvidableError(dependency)

    def register(self, dependency: Dependency, tags: Iterable[Union[str, Tag]]):
        for tag in tags:
            if isinstance(tag, str):
                tag = Tag(tag)

            if tag.name not in self._tagged_dependencies:
                self._tagged_dependencies[tag.name] = {dependency: tag}
            elif dependency not in self._tagged_dependencies[tag.name]:
                self._tagged_dependencies[tag.name][dependency] = tag
            else:
                raise DuplicateTagError(tag.name)
