import collections.abc as c_abc
from typing import Any, Iterable, Mapping, Set, Dict, Hashable

from .container import DependencyContainer, DependencyInstance
from .exceptions import DependencyNotFoundError


class ProxyContainer(DependencyContainer):
    """
    Proxy core which should only be used for mocking an testing.
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

        new_singletons = {}    # type: Dict[Any, DependencyInstance]
        if include is None:
            new_singletons = container.singletons
        elif isinstance(include, c_abc.Iterable):
            existing_singletons = container.singletons
            for dependency in include:
                new_singletons[dependency] = existing_singletons[dependency]
        else:
            raise ValueError("include must be either an iterable or None")

        if isinstance(exclude, c_abc.Iterable):
            for dependency in exclude:
                try:
                    del new_singletons[dependency]
                except KeyError:
                    pass
        elif exclude is not None:
            raise ValueError("exclude must be either an iterable or None")
        self.update_singletons({
            k: v.instance
            for k, v in new_singletons.items()
        })

        if isinstance(dependencies, c_abc.Mapping):
            self.update_singletons(dependencies)
        elif dependencies is not None:
            raise ValueError("dependencies must be either a mapping or None")

    def provide(self, dependency: Hashable):
        if dependency in self._missing:
            raise DependencyNotFoundError(dependency)

        return super().provide(dependency)
