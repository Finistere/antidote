from typing import Hashable, Iterable, List

from .._internal import API


@API.public
class AntidoteError(Exception):
    """ Base class of all errors of antidote. """

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self})"


@API.public
class DoubleInjectionError(AntidoteError):
    """
    Raised when injecting a function/method that already has been injected.
    """

    def __init__(self, func: object) -> None:
        super().__init__(f"Object {func} has already been injected by Antidote.")


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

    def __init__(self, dependency: Hashable, stack: List[Hashable] = None) -> None:
        from .._internal.utils import debug_repr
        msg = f"Could not instantiate {debug_repr(dependency)}"
        stack = (stack or [])
        if stack:  # first and last dependency will raise their own errors.
            stack.append(dependency)
            msg += f"\nFull dependency stack:\n{_stack_repr(stack)}\n"

        super().__init__(msg)


@API.public
class DependencyCycleError(AntidoteError):
    """
    A dependency cycle is found.
    """

    def __init__(self, stack: List[Hashable]) -> None:
        super().__init__(f"Cycle:\n{_stack_repr(stack)}\n")


@API.public
class DependencyNotFoundError(AntidoteError):
    """
    The dependency could not be found.
    """

    def __init__(self, dependency: Hashable) -> None:
        from .._internal.utils import debug_repr
        super().__init__(debug_repr(dependency))


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


@API.private
def _stack_repr(stack: Iterable[object]) -> str:
    from .._internal.utils import debug_repr
    import textwrap

    text = []
    for depth, dependency in enumerate(stack):
        indent = '    ' * (depth - 1) if depth > 1 else ''
        first_line, *rest = debug_repr(dependency).split("\n", 1)
        text.append(f"{indent}{'└── ' if depth else ''}{first_line}")
        if rest:
            text.append(textwrap.indent(rest[0], indent + ('    ' if depth > 1 else '')))
    return '\n'.join(text)
