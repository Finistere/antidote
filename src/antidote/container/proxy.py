import collections.abc as c_abc
from typing import Any, Iterable, Mapping, Set

from .container import DependencyContainer
from ..exceptions import DependencyNotFoundError


class ProxyContainer(DependencyContainer):
    """
    Proxy container which should only be used for mocking an testing.
    """
    def __init__(self,
                 container: DependencyContainer,
                 dependencies: Mapping = None,
                 include: Iterable = None,
                 exclude: Iterable = None,
                 missing: Iterable = None):
        super().__init__()
        for provider in container.providers.values():
            self.register_provider(provider)

        if missing is None:
            self._missing = set()  # type: Set[Any]
        elif isinstance(missing, c_abc.Iterable):
            self._missing = set(missing)
        else:
            raise ValueError("missing must be either an iterable or None")

        existing_singletons = container.singletons
        if include is None:
            self.update(existing_singletons)
        elif isinstance(include, c_abc.Iterable):
            for dependency in include:
                self[dependency] = existing_singletons[dependency]
        else:
            raise ValueError("include must be either an iterable or None")

        if isinstance(exclude, c_abc.Iterable):
            for dependency in exclude:
                try:
                    del self[dependency]
                except KeyError:
                    pass
        elif exclude is not None:
            raise ValueError("exclude must be either an iterable or None")

        if isinstance(dependencies, c_abc.Mapping):
            self.update(dependencies)
        elif dependencies is not None:
            raise ValueError("dependencies must be either a mapping or None")

    def provide(self, dependency):
        if dependency in self._missing:
            raise DependencyNotFoundError(dependency)

        return super().provide(dependency)
