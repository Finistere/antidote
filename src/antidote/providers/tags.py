from typing import Dict, Generic, Iterable, TypeVar, Union, Tuple

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


class Tagged(Generic[T]):
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
        if isinstance(dependency.id, Tag):
            name = dependency.id.name
            if name in self._tagged_dependencies:
                filter_ = dependency.kwargs.get('filter', lambda _: True)
                return Instance(Tagged({
                    self._container[dependency]: tag
                    for dependency, tag in self._tagged_dependencies[name].items()
                    if filter_(tag)
                }))

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
