import collections.abc as c_abc
from typing import Any, Iterable, Mapping, Set

from .base import DependencyContainer
from ..exceptions import DependencyNotFoundError


class ProxyContainer(DependencyContainer):
    def __init__(self,
                 container: DependencyContainer,
                 dependencies: Mapping = None,
                 include: Iterable = None,
                 exclude: Iterable = None,
                 missing: Iterable = None):
        super().__init__()
        self.providers = container.providers.copy()

        if missing is None:
            self._missing = set()  # type: Set[Any]
        elif isinstance(missing, c_abc.Iterable):
            self._missing = set(missing)
        else:
            raise ValueError("missing must be either an iterable or None")

        if include is None:
            self._singletons = container._singletons.copy()
        elif isinstance(include, c_abc.Iterable):
            for dependency in include:
                self._singletons[dependency] = container._singletons[dependency]
        else:
            raise ValueError("include must be either an iterable or None")

        if isinstance(exclude, c_abc.Iterable):
            for dependency in exclude:
                try:
                    del self._singletons[dependency]
                except KeyError:
                    pass
        elif exclude is not None:
            raise ValueError("exclude must be either an iterable or None")

        if isinstance(dependencies, c_abc.Mapping):
            self._singletons.update(dependencies)
        elif dependencies is not None:
            raise ValueError("dependencies must be either a mapping or None")

    def __getitem__(self, dependency):
        if dependency in self._missing:
            raise DependencyNotFoundError(dependency)

        return super().__getitem__(dependency)
