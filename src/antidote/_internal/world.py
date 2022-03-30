"""
Utilities used by world, mostly for syntactic sugar.
"""
from __future__ import annotations

import warnings
from typing import (Any, Callable, cast, Generic, Hashable, Optional, overload, Type,
                    TYPE_CHECKING,
                    TypeVar,
                    Union)

from typing_extensions import final, Protocol

from . import API
from .state import current_container
from .utils import Default, enforce_type_if_possible
from .utils.immutable import FinalImmutable, Immutable
from .utils.meta import Singleton
from ..core._annotations import extract_annotated_dependency
from ..core.annotations import Get
from ..core.container import RawContainer
from ..core.exceptions import DependencyNotFoundError
from ..core.typing import CallableClass, Dependency, Source
from ..extension.predicates import interface, PredicateConstraint

if TYPE_CHECKING:
    pass

T = TypeVar('T')
R = TypeVar('R')


@API.private
class SupportsRMatmul(Protocol):
    def __rmatmul__(self, type_hint: object) -> Hashable:
        pass  # pragma: no cover


@API.private
@final
class LazyDependency(Immutable, Generic[T]):
    """
    Recommended usage is to usage :py:func:`..world.lazy`:

    .. doctest:: core_utils_dependency

        >>> from antidote import Service, world
        ... class MyService(Service):
        ...     pass
        >>> port = world.lazy[MyService]()
        >>> port.get()
        <MyService ...>

    """
    __slots__ = ('unwrapped', '_type')
    unwrapped: Hashable
    """Actual dependency to be retrieved"""
    _type: Type[T]

    def __init__(self,
                 __dependency: Hashable,
                 expected_type: Type[T]) -> None:
        """
        Args:
            __dependency: actual dependency to be retrieved.
        """
        super().__init__(__dependency, expected_type)

    def get(self) -> T:
        """
        Returns:
            dependency value retrieved from :py:mod:`~..world`.
        """
        from antidote import world
        value = world.get(cast(Any, self.unwrapped))

        if not isinstance(value, self._type):
            raise TypeError(f"Dependency is not an instance of {self._type}, "
                            f"but {type(value)}")

        return value


@API.private  # use world.get, not the class directly
@final
class WorldGet(Singleton):
    @overload
    def __call__(self,
                 __dependency: Dependency[T],
                 *,
                 default: Union[T, Default] = Default.sentinel
                 ) -> T:
        ...  # pragma: no cover

    @overload
    def __call__(self,
                 __dependency: Type[T],
                 *,
                 default: Union[T, Default] = Default.sentinel
                 ) -> T:
        ...  # pragma: no cover

    @overload
    def __call__(self,
                 __dependency: Type[T],
                 *,
                 default: Union[T, Default] = Default.sentinel,
                 source: Union[Source[T], Callable[..., T], Type[CallableClass[T]]]
                 ) -> T:
        ...  # pragma: no cover

    @API.public
    def __call__(self,
                 __dependency: Any,
                 *,
                 default: Any = Default.sentinel,
                 source: Optional[Union[
                     Source[Any],
                     Callable[..., Any],
                     Type[CallableClass[Any]]
                 ]] = None
                 ) -> Any:
        if isinstance(__dependency, Get):
            __dependency = __dependency.dependency
        __dependency = cast(Any, extract_annotated_dependency(__dependency))
        if source is not None:
            __dependency = Get(__dependency, source=source).dependency
        try:
            return current_container().get(__dependency)
        except DependencyNotFoundError:
            if default is not Default.sentinel:
                return default
            raise

    @API.public
    def __getitem__(self, tpe: Type[T]) -> TypedWorldGet[T]:
        return TypedWorldGet(tpe)


@API.private  # use world.get, not the class directly
@final
class TypedWorldGet(Generic[T], FinalImmutable):
    __slots__ = ('__type',)
    __type: Type[T]

    @overload
    def __call__(self,
                 __dependency: Any,
                 *,
                 default: Union[T, Default] = Default.sentinel
                 ) -> T:
        ...  # pragma: no cover

    @overload
    def __call__(self,
                 *,
                 default: Union[T, Default] = Default.sentinel,
                 ) -> T:
        ...  # pragma: no cover

    @overload
    def __call__(self,
                 __dependency: Type[R],
                 *,
                 default: Union[T, Default] = Default.sentinel,
                 source: Union[Source[R], Callable[..., R], Type[CallableClass[R]]]
                 ) -> T:
        ...  # pragma: no cover

    @overload
    def __call__(self,
                 *,
                 default: Union[T, Default] = Default.sentinel,
                 source: Union[Source[T], Callable[..., T], Type[CallableClass[T]]]
                 ) -> T:
        ...  # pragma: no cover

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
        if isinstance(__dependency, Get):
            __dependency = __dependency.dependency

        if __dependency is None:
            __dependency = extract_annotated_dependency(self.__type)
        else:
            __dependency = extract_annotated_dependency(__dependency)
        if source is not None:
            __dependency = Get(cast(Any, __dependency), source=source).dependency
        try:
            value = current_container().get(__dependency)
        except DependencyNotFoundError:
            if default is not Default.sentinel:
                return default
            raise

        assert enforce_type_if_possible(value, self.__type)
        return value

    @API.public
    def single(self,
               *constraints: PredicateConstraint[Any],
               qualified_by: Optional[list[object]] = None,
               qualified_by_one_of: Optional[list[object]] = None,
               qualified_by_instance_of: Optional[type] = None
               ) -> T:
        return self(interface[self.__type].single(
            *constraints,
            qualified_by=qualified_by,
            qualified_by_one_of=qualified_by_one_of,
            qualified_by_instance_of=qualified_by_instance_of)
        )

    @API.public
    def all(self,
            *constraints: PredicateConstraint[Any],
            qualified_by: Optional[list[object]] = None,
            qualified_by_one_of: Optional[list[object]] = None,
            qualified_by_instance_of: Optional[type] = None
            ) -> list[T]:
        from antidote import world
        value = world.get(interface[self.__type].all(
            *constraints,
            qualified_by=qualified_by,
            qualified_by_one_of=qualified_by_one_of,
            qualified_by_instance_of=qualified_by_instance_of)
        )

        enforce_type_if_possible(value, list)
        x: object
        for x in value:
            assert enforce_type_if_possible(x, self.__type)

        return value

    @API.public
    def __matmul__(self, other: SupportsRMatmul) -> T:
        warnings.warn("Prefer the Get(dependency, source=X) notation.",
                      DeprecationWarning)
        return self.__call__(self.__type @ other)


@API.private
@final
class WorldLazy(Singleton):
    def __call__(self, __dependency: Hashable) -> LazyDependency[object]:
        warnings.warn("Deprecated behavior, wrap world.get() yourself", DeprecationWarning)
        return LazyDependency(__dependency, object)

    def __getitem__(self, tpe: Type[T]) -> TypedWorldLazy[T]:
        warnings.warn("Deprecated behavior, wrap world.get() yourself", DeprecationWarning)
        return TypedWorldLazy(tpe)


@API.private
@final
class TypedWorldLazy(Generic[T], Immutable):
    __slots__ = ('__type',)
    __type: Type[T]

    def __call__(self, __dependency: Hashable = None) -> LazyDependency[T]:
        warnings.warn("Deprecated behavior, wrap world.get() yourself", DeprecationWarning)
        return LazyDependency[T](self.__type if __dependency is None else __dependency,
                                 self.__type)

    def __matmul__(self, other: SupportsRMatmul) -> LazyDependency[T]:
        return self.__call__(self.__type @ other)


@API.private
def new_container() -> RawContainer:
    """ default new container in Antidote """

    from .._providers import (LazyProvider, ServiceProvider,
                              IndirectProvider, FactoryProvider)

    container = RawContainer()
    container.add_provider(FactoryProvider)
    container.add_provider(LazyProvider)
    container.add_provider(IndirectProvider)
    container.add_provider(ServiceProvider)

    return container
