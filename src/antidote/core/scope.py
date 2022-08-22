from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, cast, Generic, TYPE_CHECKING, TypeVar

from typing_extensions import final

from .._internal import API, auto_detect_var_name, Default, enforce_valid_name
from ._scope import AbstractScopeVar
from .data import CatalogId

if TYPE_CHECKING:
    from . import Catalog

__all__ = ["ScopeGlobalVar", "ScopeVarToken", "Missing"]

T = TypeVar("T")
SVar = TypeVar("SVar", bound=AbstractScopeVar[Any])


@API.public
@final
@dataclass(frozen=True, eq=False)
class ScopeGlobalVar(AbstractScopeVar[T]):
    """
    Declares a scope variable, a dependency with a value that can be updated at any moment. A
    similar API to :py:class:`~contextvars.ContextVar` is exposed. Either:py:meth:~.ScopeGlobalVar.set`
    or :py:meth:~.ScopeGlobalVar.reset` can be used to update the value.

    .. doctest:: core_scope_var

        >>> from antidote import ScopeGlobalVar, world
        >>> current_name = ScopeGlobalVar(default="Bob")
        >>> world[current_name]
        'Bob'
        >>> current_name.set("Alice")
        ScopeVarToken(old_value='Bob', ...)
        >>> world[current_name]
        'Alice'

    It can be easily used as a context manager:

    .. doctest:: core_scope_var

        >>> from typing import Iterator
        >>> from contextlib import contextmanager
        >>> @contextmanager
        ... def name_of(name: str) -> Iterator[None]:
        ...     token = current_name.set(name)
        ...     try:
        ...         yield
        ...     finally:
        ...         current_name.reset(token)
        >>> with name_of('John'):
        ...     world[current_name]
        'John'

    Scope variable have a special treatment as they impact the lifetime of their dependents.

    1. A singleton cannot depend on a scope variable. It wouldn't take into account the updates.

    .. doctest:: core_scope_var

        >>> from antidote import injectable, inject
        >>> @injectable
        ... class Dummy:
        ...     def __init__(self, name: str = inject[current_name]) -> None:
        ...         pass
        >>> world[Dummy]
        Traceback (most recent call last):
          File "<stdin>", line 1, in ?
        DependencyDefinitionError: Singletons cannot depend on any scope...

    If yout need access to a scope variable within a singleton, it should be injected on a method
    instead:

    .. doctest:: core_scope_var

        >>> from antidote import injectable, inject
        >>> @injectable
        ... class Dummy:
        ...     # Use the current name for a specific task
        ...     def process(self, name: str = inject[current_name]) -> int:
        ...         return len(name)
        >>> world[Dummy].process()
        5

    2. Whenever a scope variable is updated, all of its dependents with a :py:obj:`~.LifeTime.SCOPED`
       lifetime will be re-computed lazily.

    .. doctest:: core_scope_var

        >>> from antidote import lazy
        >>> @lazy.value(lifetime='scoped')
        ... def length(name: str = inject[current_name]) -> int:
        ...     return len(name)
        >>> world[length]
        5
        >>> world[length]  # returns the same, cached, object
        5
        >>> current_name.set("Unknown")
        ScopeVarToken(old_value='Alice', ...)
        >>> world[length]
        7

    .. note::

        The :py:class:`.ScopeGlobalVar` creates a global variable and not a
        :py:class:`~contextvars.ContextVar`. It's the same for all threads and coroutines.

    """

    __slots__ = ()
    name: str
    catalog_id: CatalogId

    def __init__(
        self,
        *,
        default: T | Default = Default.sentinel,
        name: str | Default = Default.sentinel,
        catalog: Catalog | Default = Default.sentinel,
    ) -> None:
        if isinstance(name, Default):
            name = auto_detect_var_name()
        else:
            enforce_valid_name(name)

        super().__init__(name=name, default=default, catalog=catalog)

    def set(self, __value: T) -> ScopeVarToken[T, ScopeGlobalVar[T]]:
        return cast(ScopeVarToken[T, ScopeGlobalVar[T]], super().set(__value))

    def reset(self, __token: ScopeVarToken[T, ScopeGlobalVar[T]]) -> None:
        return super().reset(__token)

    @API.private  # You can obviously use repr, but its content is not part of the public API.
    def __repr__(self) -> str:
        return f"ScopeGlobalVar(name={self.name}, catalog_id={self.catalog_id})"

    @API.private
    def __antidote_debug_repr__(self) -> str:
        return f"<scope-global-var> {self.name}"


@API.public
@final
@dataclass(frozen=True, eq=False)
class ScopeVarToken(Generic[T, SVar]):
    __slots__ = ("old_value", "var")
    old_value: T | Missing
    var: SVar


@API.public
@final
class Missing(enum.Enum):
    SENTINEL = enum.auto()
