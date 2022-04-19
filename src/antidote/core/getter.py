from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import (Any, Callable, cast, Generic, List, Optional, overload, Type, TYPE_CHECKING,
                    TypeVar,
                    Union)

from typing_extensions import final, Protocol

from ._annotations import extract_annotated_dependency
from .annotations import Get
from .typing import CallableClass, Dependency, Source
from .._internal import API
from .._internal.utils import Default, enforce_type_if_possible

T = TypeVar('T')
R = TypeVar('R')

if TYPE_CHECKING:
    from ..lib.interface import PredicateConstraint


@API.private
class DependencyLoader(Protocol):
    def __call__(self, dependency: object, default: object) -> Any:
        ...


@API.private
class SupportsRMatmul(Protocol):
    def __rmatmul__(self, type_hint: object) -> object:
        ...


@API.private  # rely on world.get or inject.get
@final
@dataclass(frozen=True)
class DependencyGetter:
    __slots__ = ('__enforce_type', '__load')
    __enforce_type: bool
    __load: DependencyLoader

    @classmethod
    @API.private
    def enforced(cls, loader: DependencyLoader) -> DependencyGetter:
        return DependencyGetter(True, loader)

    @classmethod
    @API.private
    def raw(cls, loader: DependencyLoader) -> DependencyGetter:
        return DependencyGetter(False, loader)

    @overload
    def __call__(self,
                 __dependency: Dependency[T],
                 *,
                 default: Union[T, Default] = Default.sentinel
                 ) -> T:
        ...

    @overload
    def __call__(self,
                 __dependency: Type[T],
                 *,
                 default: Union[T, Default] = Default.sentinel
                 ) -> T:
        ...

    @overload
    def __call__(self,
                 __dependency: Type[T],
                 *,
                 source: Union[Source[T], Callable[..., T], Type[CallableClass[T]]],
                 default: Union[T, Default] = Default.sentinel
                 ) -> T:
        ...

    @API.public
    def __call__(self,
                 __dependency: Union[Type[T], Dependency[T]],
                 *,
                 source: Any = None,
                 default: Union[T, Default] = Default.sentinel
                 ) -> T:
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
            source: Source of the dependency if any, typically a factory.

        Returns:

        """
        __dependency = cast(Any, extract_annotated_dependency(__dependency))
        if source is not None:
            if isinstance(__dependency, Dependency):
                raise TypeError("When specifying a source, the dependency must be a class")
            __dependency = cast(Dependency[T], Get(__dependency, source=source).dependency)
        return cast(T, self.__load(__dependency, default))

    def __getitem__(self, tpe: Type[T]) -> TypedDependencyGetter[T]:
        """

        Args:
            tpe: Type to use as reference

        Returns:

        """
        return TypedDependencyGetter[T](self.__enforce_type, self.__load, tpe)


@API.private  # use world.get, not the class directly
@final
@dataclass(frozen=True)
class TypedDependencyGetter(Generic[T]):
    __slots__ = ('__enforce_type', '__load', '__type')
    __enforce_type: bool
    __load: DependencyLoader
    __type: Type[T]

    @overload
    def __call__(self,
                 *,
                 default: Union[T, Default] = Default.sentinel,
                 ) -> T:
        ...

    @overload
    def __call__(self,
                 *,
                 default: Union[T, Default] = Default.sentinel,
                 source: Union[Source[T], Callable[..., T], Type[CallableClass[T]]]
                 ) -> T:
        ...

    @overload
    def __call__(self,
                 __dependency: Any,
                 *,
                 default: Union[T, Default] = Default.sentinel
                 ) -> T:
        ...

    @overload
    def __call__(self,
                 __dependency: Type[R],
                 *,
                 default: Union[T, Default] = Default.sentinel,
                 source: Union[Source[R], Callable[..., R], Type[CallableClass[R]]]
                 ) -> T:
        ...

    @API.public
    def __call__(self,
                 __dependency: Any = None,
                 *,
                 default: Union[T, Default] = Default.sentinel,
                 source: Optional[Union[
                     Source[Any],
                     Callable[..., Any],
                     Type[CallableClass[Any]]
                 ]] = None
                 ) -> T:
        if default is not Default.sentinel \
                and isinstance(self.__type, type) \
                and not isinstance(default, self.__type):
            raise TypeError(f"Default value {default} is not an instance of {self.__type}, "
                            f"but a {type(default)}")
        if __dependency is None:
            warnings.warn("Omitting the dependency is deprecated. "
                          "Use directly `world.get(dependency)`, it will be correctly typed.",
                          DeprecationWarning)
            __dependency = extract_annotated_dependency(self.__type)
        else:
            __dependency = extract_annotated_dependency(__dependency)
        if source is not None:
            __dependency = Get(cast(Any, __dependency), source=source).dependency
        value = self.__load(__dependency, default=default)
        if self.__enforce_type:
            assert enforce_type_if_possible(value, self.__type)
        return cast(T, value)

    @API.public
    def single(self,
               *constraints: PredicateConstraint[Any],
               qualified_by: Optional[object | list[object]] = None,
               qualified_by_one_of: Optional[list[object]] = None
               ) -> T:
        """
        .. versionadded:: 1.2

        Retrieve a single implementation matching given constraints. If multiple or no
        implementation is found, an error will be raised upon retrieval.

        Args:
            *constraints: :py:class:`.PredicateConstraint` to evaluate for each implementation.
            qualified_by: All specified qualifiers must qualify the implementation.
            qualified_by_one_of: At least one of the specified qualifiers must qualify the
                implementation.
        """
        from ..lib.interface import ImplementationsOf
        dependency = ImplementationsOf[T](self.__type).single(
            *constraints,
            qualified_by=qualified_by,
            qualified_by_one_of=qualified_by_one_of
        )
        return self(dependency)

    @API.public
    def all(self,
            *constraints: PredicateConstraint[Any],
            qualified_by: Optional[object | list[object]] = None,
            qualified_by_one_of: Optional[list[object]] = None
            ) -> list[T]:
        """
        .. versionadded:: 1.2

        Retrieve all implementations matching given constraints.

        Args:
            *constraints: :py:class:`.PredicateConstraint` to evaluate for each implementation.
            qualified_by: All specified qualifiers must qualify the implementation.
            qualified_by_one_of: At least one of the specified qualifiers must qualify the
                implementation.
        """
        from ..lib.interface import ImplementationsOf
        dependency = ImplementationsOf[T](self.__type).all(
            *constraints,
            qualified_by=qualified_by,
            qualified_by_one_of=qualified_by_one_of
        )
        value = self.__load(dependency, Default.sentinel)

        if self.__enforce_type:
            assert enforce_type_if_possible(value, list)
            x: object
            for x in cast(List[object], value):
                assert enforce_type_if_possible(x, self.__type)

        return cast(List[T], value)

    @API.deprecated
    def __matmul__(self, other: SupportsRMatmul) -> T:
        warnings.warn("Prefer the Get(dependency, source=X) notation.",
                      DeprecationWarning)
        return self.__call__(self.__type @ other)
