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
    "TestEnvKind",
    "TestEnv",
    "CatalogId",
    "Missing",
]

T = TypeVar("T")
Out = TypeVar("Out", covariant=True)


@API.public
@final
class Missing(enum.Enum):
    SENTINEL = enum.auto()


@API.experimental
@final
class TestEnvKind(enum.Enum):
    EMPTY = 1
    NEW = 2
    CLONE = 3
    COPY = 4


@API.experimental
class TestEnv(Protocol):
    @property
    def kind(self) -> TestEnvKind:
        ...


@API.public
@final
@dataclass(frozen=True)
class CatalogId:
    """
    Unique identifier of a catalog. :code:`name` stays the same across test environments such as
    :py:meth:`~.TestCatalogBuilder.clone`. :code:`test_env` will contain information related to
    the test environment used on the catalog.
    """

    __slots__ = ("name", "test_env")
    name: str
    test_env: tuple[TestEnv, ...]

    def __init__(self, name: str, test_env: tuple[TestEnv, ...] = tuple()) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "test_env", test_env)

    @API.private
    def within_env(self, env: TestEnv) -> CatalogId:
        return CatalogId(name=self.name, test_env=self.test_env + (env,))

    @API.private  # no guarantees are made on the content except to be exhaustive.
    def __str__(self) -> str:
        return f"{self.name}[{', '.join(map(str, self.test_env))}]"


@API.public
@final
class LifeTime(Enum):
    """
    The lifetime of a dependency defines how long its value is kept by the :py:class:`.Catalog`:

    - 'bound': The value is kept until any :py:func:`.state` dependency is updated. All direct and
        transitive :py:func:`.state` dependencies are taken into account.
    - 'singleton': The value is computed only once.

    If the lifetime is :py:obj:`None`, the value will never be kept and re-computed each time.
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
    Wraps a dependency and defines the actual type of the dependency value to expect. Both
    :py:class:`.Catalog` and :py:obj:`.inject` support custom subclasses. By default, the object
    itself is the dependency. Subclassing it in this case has the only purpose of specifying the
    actual dependency value type.
    """

    def __antidote_dependency_hint__(self) -> Out:
        return cast(Out, self)


@API.public
class ParameterDependency(ABC):
    """
    Defines the dependency to inject based on the argument name and type hints when using
    :py:obj:`.inject`. This is how :py:meth:`~.Injector.me` and :py:obj:`.Inject` work underneath.
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
        while True:
            if isinstance(__dependency, dependencyOf):
                default = __dependency.default if default is Default.sentinel else default
                __dependency = __dependency.wrapped
                break
            elif isinstance(__dependency, Dependency):
                real_dependency: object = __dependency.__antidote_dependency_hint__()
                if isinstance(real_dependency, Dependency) and real_dependency is not __dependency:
                    __dependency = real_dependency
                else:
                    __dependency = real_dependency
                    break
            # it's a type alias
            elif not isinstance(__dependency, type) and isinstance(get_origin(__dependency), type):
                from ..lib.interface import instanceOf

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
    wired: Sequence[object]
    dependencies: Sequence[object]

    def __init__(
        self,
        *,
        description: str,
        lifetime: LifetimeType | None,
        wired: Callable[..., Any] | Sequence[object] = tuple(),
        dependencies: Sequence[object] = tuple(),
    ) -> None:
        """
        Args:
            description: Concise description of the dependency.
            lifetime: Scope of the dependency
            wired: All objects wired for this dependency. All of those will be treated as child
                dependencies in the tree and their injected dependencies will appear underneath.
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
