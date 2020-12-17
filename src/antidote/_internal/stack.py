from contextlib import contextmanager
from typing import Hashable, Iterator, List

from ..core.exceptions import DependencyCycleError


class DependencyStack:
    """
    Stores the stack of dependency instantiation to detect and prevent cycles
    by raising DependencyCycleError.

    Used in the Container.

    This class is not thread-safe by itself.
    """

    def __init__(self) -> None:
        self._stack: List[Hashable] = list()

    @property
    def depth(self) -> int:
        return len(self._stack)

    def to_list(self) -> List[Hashable]:
        return self._stack.copy()

    @contextmanager
    def instantiating(self, dependency: Hashable) -> Iterator[None]:
        """
        Context Manager which has to be used when instantiating the
        dependency to keep track of the dependency path.

        When a cycle is detected, a DependencyCycleError is raised.
        """
        if dependency in self._stack:
            raise DependencyCycleError(self._stack + [dependency])

        self._stack.append(dependency)
        try:
            yield
        finally:
            self._stack.pop()
