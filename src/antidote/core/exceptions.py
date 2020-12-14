import inspect
from typing import Any, Hashable, List, Optional, Tuple

from .._internal import API


@API.public
class AntidoteError(Exception):
    """ Base class of all errors of antidote. """

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self})"


@API.public
class DuplicateDependencyError(AntidoteError):
    """
    A dependency already exists with the same id.
    *May* be raised by _providers.
    """


@API.public
class DependencyInstantiationError(AntidoteError):
    """
    The dependency could not be instantiated.
    """

    def __init__(self, dependency: Hashable) -> None:
        super().__init__(f"Could not instantiate {dependency}")


@API.public
class DependencyCycleError(AntidoteError):
    """
    A dependency cycle is found.
    """

    def __init__(self, dependencies: List[Hashable]) -> None:
        self.dependencies = dependencies

    def __str__(self) -> str:
        return "Cycle:" + ''.join(map(self._repr, enumerate(self.dependencies))) + "\n"

    @staticmethod
    def _repr(i_dep: Tuple[int, Hashable]) -> str:
        index, dependency = i_dep
        if inspect.isclass(dependency):
            return f"\n    {index}: {dependency.__module__}" \
                   f".{getattr(dependency, '__name__', dependency)}"

        return f"\n    {index}: {repr(dependency)}"


@API.public
class DependencyNotFoundError(AntidoteError):
    """
    The dependency could not be found.
    """

    def __init__(self, dependency: Hashable) -> None:
        self.missing_dependency = dependency

    def __str__(self) -> str:
        return repr(self.missing_dependency)


@API.public
class FrozenWorldError(AntidoteError):
    """
    An action failed because the world is frozen. Typically happens when trying
    to register a dependency after having called freeze() on the world.
    """


@API.private
class DebugNotAvailableError(AntidoteError):
    """
    Currently provider do not have to implement the debug behavior. If not, this error
    will be raised and discarded (a warning may be emitted).
    """
