import inspect
from collections import deque
from contextlib import contextmanager
from typing import Iterable

from ..exceptions import DependencyCycleError


class InstantiationStack:
    """
    Stores the stack of dependency instantiation to detect and prevent cycles
    by raising DependencyCycleError.

    Used in the DependencyContainer.

    This class is not thread-safe by itself.
    """

    def __init__(self, stack: Iterable = None) -> None:
        self._stack = deque(stack or [])
        self._dependencies = set(self._stack)

    def __repr__(self):
        return "{}({})".format(
            type(self).__name__,
            self.format_stack()
        )

    def __iter__(self):
        return iter(self._stack)

    def format_stack(self, sep: str = ' => ') -> str:
        """
        Returns a human readable representation of the current stack.
        """
        return sep.join(map(self._format_dependency_id, self._stack))

    @classmethod
    def _format_dependency_id(cls, dependency_id) -> str:
        if inspect.isclass(dependency_id):
            return "{}.{}".format(dependency_id.__module__,
                                  dependency_id.__name__)

        return repr(dependency_id)

    @contextmanager
    def instantiating(self, dependency_id):
        """
        Context Manager which has to be used when instantiating the
        dependency to keep track of the dependency path.

        When a cycle is detected, a DependencyCycleError is raised.
        """
        if dependency_id in self._dependencies:
            self._stack.append(dependency_id)
            message = self.format_stack()
            self._clear()
            raise DependencyCycleError(message)

        self._stack.append(dependency_id)
        self._dependencies.add(dependency_id)
        try:
            yield
        except Exception:
            self._clear()
            raise
        else:
            self._dependencies.remove(self._stack.pop())

    def _clear(self):
        self._stack = deque()
        self._dependencies = set()
