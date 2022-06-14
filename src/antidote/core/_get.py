from __future__ import annotations

from typing import Any, Callable, Optional, overload, Type, TYPE_CHECKING, TypeVar

from typing_extensions import ParamSpec, Protocol

from .._internal import API
from .._internal.typing import Function
from .data import Dependency, dependencyOf

T = TypeVar("T")
U = TypeVar("U")
R = TypeVar("R")
P = ParamSpec("P")

if TYPE_CHECKING:
    from ..lib.interface import instanceOf


@API.private
class DependencyLoader(Protocol):
    def __call__(self, __dependency: dependencyOf[object]) -> Any:
        ...


@API.private
class DependencyAccessorImpl:
    __slots__ = ("__loader",)
    __loader: Function[[dependencyOf[object]], object]

    @overload
    def get(
        self,
        __dependency: Dependency[T] | Type[instanceOf[T]],
    ) -> Optional[T]:
        ...

    @overload
    def get(
        self,
        __dependency: Type[T],
    ) -> Optional[T]:
        ...

    @overload
    def get(
        self,
        __dependency: object,
    ) -> Optional[object]:
        ...

    @overload
    def get(self, __dependency: Dependency[T] | Type[instanceOf[T]], default: U) -> T | U:
        ...

    @overload
    def get(self, __dependency: Type[T], default: U) -> T | U:
        ...

    @overload
    def get(self, __dependency: Callable[P, Dependency[T]], default: U) -> Callable[P, T] | U:
        ...

    @overload
    def get(self, __dependency: object, default: object) -> object:
        ...

    def get(
        self,
        __dependency: Any,
        default: object = None,
    ) -> object:
        """
        Retrieve the specified dependency. The interface is the same for both :py:obj:`.inject` and
        :py:obj:`.world`:

        .. doctest:: core_getter_getter

            >>> from antidote import world, injectable, inject
            >>> @injectable
            ... class Dummy:
            ...     pass
            >>> world.get(Dummy)
            <Dummy object at ...>
            >>> @inject
            ... def f(dummy = inject.get(Dummy)) -> Dummy:
            ...     return dummy
            >>> f()
            <Dummy object at ...>

        Args:
            __dependency: dependency to retrieve.
            default: Default value to use if the dependency could not be retrieved. By default
                an error is raised.

        Returns:

        """
        return self.__loader(dependencyOf(__dependency, default=default))

    @overload
    def __getitem__(self, __dependency: Dependency[T] | Type[instanceOf[T]]) -> T:
        ...

    @overload
    def __getitem__(self, __dependency: Type[T]) -> T:
        ...

    @overload
    def __getitem__(self, __dependency: Callable[P, Dependency[T]]) -> Callable[P, T]:
        ...

    @overload
    def __getitem__(self, __dependency: object) -> object:
        ...

    def __getitem__(self, __dependency: Any) -> object:
        return self.__loader(dependencyOf(__dependency))

    def __init__(self, *, loader: Callable[[dependencyOf[object]], object]) -> None:
        object.__setattr__(self, f"_{DependencyAccessorImpl.__name__}__loader", loader)
