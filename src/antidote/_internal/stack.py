from contextlib import contextmanager

from ..exceptions import DependencyCycleError


class DependencyStack:
    """
    Stores the stack of dependency instantiation to detect and prevent cycles
    by raising DependencyCycleError.

    Used in the DependencyContainer.

    This class is not thread-safe by itself.
    """

    def __init__(self):
        self._stack = list()
        self._seen = set()

    @contextmanager
    def instantiating(self, dependency):
        """
        Context Manager which has to be used when instantiating the
        dependency to keep track of the dependency path.

        When a cycle is detected, a DependencyCycleError is raised.
        """
        if dependency in self._seen:
            raise DependencyCycleError(self._stack + [dependency])

        self._stack.append(dependency)
        self._seen.add(dependency)
        try:
            yield
        finally:
            self._seen.remove(self._stack.pop())
