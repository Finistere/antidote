"""
Utilities used by world, mostly for syntactic sugar.
"""
from __future__ import annotations

import warnings
from typing import (Any, cast, Generic, Hashable, Type,
                    TypeVar)

from typing_extensions import final, Protocol

from . import API
from .utils.immutable import Immutable
from .utils.meta import Singleton
from ..core.container import RawContainer

T = TypeVar('T')


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


@API.deprecated
@API.private
@final
class WorldLazy(Singleton):
    def __call__(self, __dependency: Hashable) -> LazyDependency[object]:
        warnings.warn("Deprecated behavior, wrap world.get() yourself", DeprecationWarning)
        return LazyDependency(__dependency, object)

    def __getitem__(self, tpe: Type[T]) -> TypedWorldLazy[T]:
        warnings.warn("Deprecated behavior, wrap world.get() yourself", DeprecationWarning)
        return TypedWorldLazy(tpe)


@API.deprecated
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

    from .._providers import LazyProvider, IndirectProvider, FactoryProvider
    from ..lib.interface._provider import InterfaceProvider
    from ..lib.injectable._provider import InjectableProvider

    container = RawContainer()
    container.add_provider(FactoryProvider)
    container.add_provider(LazyProvider)
    container.add_provider(IndirectProvider)
    container.add_provider(InjectableProvider)
    container.add_provider(InterfaceProvider)

    return container
