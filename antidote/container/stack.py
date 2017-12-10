import inspect
from collections import deque
from contextlib import contextmanager

from ..exceptions import DependencyCycleError


class DependencyStack(object):
    """
    Stores the stack of dependency instantiation to detect and prevent cycles
    by raising DependencyCycleError.

    Used in DependencyContainer.

    This class is not thread-safe by itself.
    """

    def __init__(self, stack=None):
        self._stack = deque(stack or [])
        self._dependencies = set(self._stack)

    def __repr__(self):
        return "{}({})".format(
            type(self).__name__,
            self.format_stack()
        )

    __str__ = __repr__

    def __iter__(self):
        return iter(self._stack)

    def format_stack(self, sep=' => '):
        return sep.join(map(self._format_dependency_id, self._stack))

    @classmethod
    def _format_dependency_id(cls, dependency_id):
        if inspect.isclass(dependency_id):
            return "{}.{}".format(dependency_id.__module__,
                                  dependency_id.__name__)

        return repr(dependency_id)

    @contextmanager
    def instantiating(self, dependency_id):
        if dependency_id in self._dependencies:
            self._stack.append(dependency_id)
            message = self.format_stack()
            self._clear()
            raise DependencyCycleError(message)

        self._stack.append(dependency_id)
        self._dependencies.add(dependency_id)
        yield
        self._dependencies.remove(self._stack.pop())

    def _clear(self):
        self._stack = deque()
        self._dependencies = set()
