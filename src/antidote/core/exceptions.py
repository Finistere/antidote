import inspect
from typing import Any, Hashable, List, Optional

from .._internal import API


@API.public
class AntidoteError(Exception):
    """ Base class of all errors of antidote. """

    def __repr__(self):
        return f"{type(self).__name__}({self})"


@API.public
class DuplicateDependencyError(AntidoteError):
    """
    A dependency already exists with the same id.
    *May* be raised by _providers.
    """
    message: Optional[str]

    def __init__(self, dependency_or_message: Hashable, existing_definition: Any = None):
        if isinstance(dependency_or_message, str) and existing_definition is None:
            self.message = dependency_or_message
        else:
            self.message = None
            self.dependency = dependency_or_message
            self.existing_definition = existing_definition

    def __str__(self):
        if self.message is not None:
            return self.message
        else:
            return f"The dependency {self.dependency} already exists. " \
                   f"It points to {self.existing_definition}."


@API.public
class DependencyInstantiationError(AntidoteError):
    """
    The dependency could not be instantiated.
    """

    def __init__(self, dependency):
        super().__init__(f"Could not instantiate {dependency}")


@API.public
class DependencyCycleError(AntidoteError):
    """
    A dependency cycle is found.
    """

    def __init__(self, dependencies: List):
        self.dependencies = dependencies

    def __str__(self):
        return "Cycle:" + ''.join(map(self._repr, enumerate(self.dependencies))) + "\n"

    @staticmethod
    def _repr(i_dep) -> str:
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

    def __init__(self, dependency: Hashable):
        self.missing_dependency = dependency

    def __str__(self):
        return repr(self.missing_dependency)


@API.public
class FrozenWorldError(AntidoteError):
    """
    An action failed because the world is frozen. Typically happens when trying
    to register a dependency after having called freeze() on the world.
    """


@API.experimental
class FrozenContainerError(FrozenWorldError):
    """
    Whenever ensure_not_frozen() fails.
    """


@API.private
class DebugNotAvailableError(AntidoteError):
    """
    Currently provider do not have to implement the debug behavior. If not, this error
    will be raised and discarded (a warning may be emitted).
    """
