from __future__ import annotations

import collections.abc
import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, cast, Optional, Sequence, TYPE_CHECKING, TypeVar

from typing_extensions import final, get_args, get_origin, Protocol, runtime_checkable

from .._internal import API, Default

if TYPE_CHECKING:
    from . import LifetimeType

__all__ = [
    "Dependency",
    "DependencyDebug",
    "dependencyOf",
    "DebugInfoPrefix",
    "ParameterDependency",
    "LifeTime",
    "TestContextKind",
    "TestContextId",
    "CatalogId",
]

T = TypeVar("T")
Out = TypeVar("Out", covariant=True)


@API.experimental
@final
class TestContextKind(enum.Enum):
    EMPTY = 1
    NEW = 2
    CLONE = 3
    COPY = 4


@API.experimental
class TestContextId(Protocol):
    @property
    def kind(self) -> TestContextKind:
        ...


@API.public
@final
@dataclass(frozen=True)
class CatalogId:
    __slots__ = ("name", "test_context_ids")
    name: str
    test_context_ids: API.Experimental[tuple[TestContextId, ...]]

    def __hash__(self) -> int:
        return object.__hash__(self)

    def __eq__(self, other: object) -> bool:
        return self is other

    def __repr__(self) -> str:
        return f"{self.name}[{', '.join(map(str, self.test_context_ids))}]"


@API.public
@final
class LifeTime(Enum):
    """
    The lifetime of a dependency defines how long its value is kept by the :py:class:`.Catalog`:

    - :code:`transient`: The value is never kept and re-computed at each request.
    - :code:`singleton`: The value is computed at most once.
    - :code:`scoped`: When depending on one or multiple :py:class:`.ScopeGlobalVar`, the value is
      re-computed if any of those change. As long as they do not, the value is cached.
    """

    TRANSIENT = 1
    SCOPED = 2
    SINGLETON = 3

    @staticmethod
    def of(__lifetime: LifetimeType) -> LifeTime:
        if isinstance(__lifetime, str):
            return dict(
                transient=LifeTime.TRANSIENT,
                scoped=LifeTime.SCOPED,
                singleton=LifeTime.SINGLETON,
            )[__lifetime]
        elif isinstance(__lifetime, LifeTime):
            return __lifetime
        raise TypeError(f"Invalid lifetime: {__lifetime!r}")


@API.public
@runtime_checkable
class Dependency(Protocol[Out]):
    """
    Protocol to be used to be used to add support for new dependencies on :py:class:`.Catalog`
    and :py:obj:`.inject`.

    A single method :py:meth:`~.Dependency.__antidote_dependency_hint__` must be defined. The
    return type hint is used to infer the type of the dependency value which will be provided.
    However, the returned object should be the dependency itself. This allows any object to wrap
    a dependency. The dependency can also be another :py:class:`.Dependency`, it will be unwrapped
    as many times as necessary.

    As the type of the dependency is rarely the same as its dependency value, you should use
    :py:func:`typing.cast` to avoid static typing errors.

    .. doctest:: core_data_dependency

        >>> from typing import Generic, TypeVar, cast
        >>> from dataclasses import dataclass
        >>> from antidote import world
        >>> T = TypeVar('T')
        >>> @dataclass
        ... class MyDependencyWrapper(Generic[T]):
        ...     wrapped: object
        ...     #                                         ⯆ Defines the type of the dependency value
        ...     def __antidote_dependency_hint__(self) -> T:
        ...         # actual dependency to be used by the catalog
        ...         return cast(T, self.wrapped)

    .. tip::

        If you only need to wrap a value and provide a type for the dependency value, consider
        simply using :py:class:`.dependencyOf` instead.

    """

    def __antidote_dependency_hint__(self) -> Out:
        return cast(Out, self)


@API.public
class ParameterDependency(ABC):
    """
    Defines the dependency to inject based on the argument name and type hints when using
    :py:obj:`.inject`. This is how :py:meth:`~.Inject.me` and :py:obj:`.Inject` work underneath.

    .. doctest:: core_data_parameter_dependency

        >>> from typing import Any
        >>> from antidote import Dependency, dependencyOf, inject, injectable, ParameterDependency, world
        >>> class Auto(ParameterDependency):
        ...     def __antidote_parameter_dependency__(self, *,
        ...                                           name: str,
        ...                                           type_hint: object,
        ...                                           type_hint_with_extras: object
        ...                                           ) -> Dependency[Any]:
        ...         if isinstance(type_hint, type):
        ...             return dependencyOf(type_hint)
        ...         raise RuntimeError()
        >>> def auto() -> Any:  # for static typing, wrapper that returns Any
        ...     return Auto()
        >>> @injectable
        ... class Service:
        ...     pass
        >>> @inject
        ... def f(service: Service = auto()) -> Service:
        ...     return service
        >>> assert f() is world[Service]

    """

    __slots__ = ()

    @abstractmethod
    def __antidote_parameter_dependency__(
        self, *, name: str, type_hint: object, type_hint_with_extras: object
    ) -> Dependency[Any]:
        raise NotImplementedError()


@API.public
@final
@dataclass(frozen=True, eq=True)
class dependencyOf(Dependency[T]):
    """
    Used by both :py:class:`.Catalog` and :py:obj:`.inject` to unwrap the actual dependency and
    define the default value to provide if any. Its main purpose is to be used typically when
    defining a custom :py:class:`.Dependency` or :py:class:`.ParameterDependency` for which a
    default value can be provided.
    """

    __slots__ = ("wrapped", "default")
    wrapped: object
    default: object

    def __init__(
        self,
        __dependency: Any,
        *,
        default: object = Default.sentinel,
    ) -> None:
        from ._raw import NotFoundSentinel

        if default is Default.sentinel:
            default = NotFoundSentinel

        while True:
            if isinstance(__dependency, dependencyOf):
                if __dependency.default is not NotFoundSentinel:
                    default = __dependency.default
                __dependency = __dependency.wrapped
                break
            elif hasattr(__dependency, "__antidote_dependency_hint__"):
                real_dependency: object = __dependency.__antidote_dependency_hint__()
                if real_dependency is __dependency:
                    break
                __dependency = real_dependency
            # it's a type alias
            elif not isinstance(__dependency, type) and isinstance(get_origin(__dependency), type):
                from ..lib.interface_ext import instanceOf

                origin = cast(Optional[type], get_origin(__dependency))
                if origin is not None and issubclass(origin, instanceOf):
                    __dependency = get_args(__dependency)[0]
                    __dependency = get_origin(__dependency) or __dependency
                else:
                    __dependency = get_origin(__dependency) or __dependency
                break
            else:
                break

        object.__setattr__(self, "wrapped", __dependency)
        object.__setattr__(self, "default", default)


@API.public
@final
@dataclass(frozen=True, eq=True)
class DependencyDebug:
    """
    Information that should be provided by a :py:class:`.Provider` when :py:meth:`.Catalog.debug` is
    called.
    """

    __slots__ = ("description", "wired", "dependencies", "lifetime")
    description: str
    lifetime: LifeTime | None
    wired: Callable[..., Any] | Sequence[Callable[..., Any]]
    dependencies: Sequence[object]

    def __init__(
        self,
        *,
        description: str,
        lifetime: LifetimeType | None,
        wired: Callable[..., Any] | Sequence[Callable[..., Any]] = tuple(),
        dependencies: Sequence[object] = tuple(),
    ) -> None:
        """
        Args:
            description: Concise description of the dependency.
            lifetime: Scope of the dependency
            wired: All objects wired for this dependency. If it's a sequence, all of those will be
                treated as child dependencies in the tree and their injected dependencies will
                appear underneath. If it's a single callable, the callable itself won't appear and
                all of its injections will appear as direct dependencies.
            dependencies: All direct dependencies.
        """
        if lifetime is not None:
            lifetime = LifeTime.of(lifetime)
        if not isinstance(description, str):
            raise TypeError(f"description must be a string, not a {type(description)!r}")
        if not (isinstance(wired, collections.abc.Sequence) or callable(wired)):
            raise TypeError(f"wired must be a Sequence or a callable, not a {type(wired)!r}")
        if not isinstance(dependencies, collections.abc.Sequence):
            raise TypeError(f"dependencies must be a Sequence, not a {type(dependencies)!r}")

        object.__setattr__(self, "description", description)
        object.__setattr__(self, "lifetime", lifetime)
        object.__setattr__(self, "wired", wired)
        object.__setattr__(self, "dependencies", dependencies)


@API.experimental
@final
@dataclass(frozen=True, eq=True)
class DebugInfoPrefix:
    """
    Allows to add a prefix before the description of the dependencies.
    """

    __slots__ = ("prefix", "dependency")
    prefix: str
    dependency: object

    def __init__(self, *, prefix: str, dependency: object) -> None:
        if not isinstance(prefix, str):
            raise TypeError(f"prefix must be a str, not a {type(prefix)!r}")
        object.__setattr__(self, "prefix", prefix)
        object.__setattr__(self, "dependency", dependency)
