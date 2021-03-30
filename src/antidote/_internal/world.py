"""
Utilities used by world, mostly for syntactic sugar.
"""
from typing import (Generic, Hashable, TYPE_CHECKING, Type, TypeVar, Union,
                    overload)

from . import API
from .state import current_container
from .utils import Default
from .utils.immutable import Immutable, ImmutableGenericMeta
from .utils.meta import FinalMeta
from .._compatibility.typing import Protocol, final
from ..core._annotations import extract_annotated_dependency
from ..core.container import RawContainer
from ..core.exceptions import DependencyNotFoundError

T = TypeVar('T')

if TYPE_CHECKING:
    from .._constants import Const


@API.private
class SupportsRMatmul(Protocol):
    def __rmatmul__(self, type_hint: object) -> Hashable:
        pass  # pragma: no cover


@API.private
@final
class LazyDependency(Immutable, Generic[T], metaclass=ImmutableGenericMeta):
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
        value = world.get(self.unwrapped)

        if not isinstance(value, self._type):
            raise TypeError(f"Dependency is not an instance of {self._type}, "
                            f"but {type(value)}")

        return value


@API.private
@final
class WorldGet(metaclass=FinalMeta):
    @overload
    def __call__(self,  # noqa: E704
                 __dependency: 'Const[T]',
                 *,
                 default: Union[T, Default] = Default.sentinel
                 ) -> T:
        ...  # pragma: no cover

    @overload
    def __call__(self,  # noqa: E704
                 __dependency: Hashable,
                 *,
                 default: object = Default.sentinel
                 ) -> object:
        ...  # pragma: no cover

    def __call__(self,
                 __dependency: Hashable,
                 *,
                 default: object = Default.sentinel
                 ) -> object:
        dependency = extract_annotated_dependency(__dependency)
        try:
            return current_container().get(dependency)
        except DependencyNotFoundError:
            if default is not Default.sentinel:
                return default
            raise

    def __getitem__(self, tpe: Type[T]) -> 'TypedWorldGet[T]':
        return TypedWorldGet(tpe)


@API.private
@final
class TypedWorldGet(Generic[T], Immutable, metaclass=ImmutableGenericMeta):
    __slots__ = ('__type',)
    __type: Type[T]

    def __call__(self,
                 __dependency: Hashable = None,
                 *,
                 default: Union[T, Default] = Default.sentinel) -> T:
        if not isinstance(default, (self.__type, Default)):
            raise TypeError(f"default is not an instance of {self.__type}, "
                            f"but {type(default)}")

        if __dependency is None:
            dependency: object = self.__type
        else:
            dependency = extract_annotated_dependency(__dependency)
        try:
            value = current_container().get(dependency)
        except DependencyNotFoundError:
            if default is not Default.sentinel:
                return default
            raise

        if not isinstance(value, self.__type):
            raise TypeError(f"Dependency is not an instance of {self.__type}, "
                            f"but {type(value)}")

        return value

    def __matmul__(self, other: SupportsRMatmul) -> T:
        return self.__call__(self.__type @ other)


@API.private
@final
class WorldLazy(metaclass=FinalMeta):
    def __call__(self, __dependency: Hashable) -> LazyDependency[object]:
        return LazyDependency(__dependency, object)

    def __getitem__(self, tpe: Type[T]) -> 'TypedWorldLazy[T]':
        return TypedWorldLazy(tpe)


@API.private
@final
class TypedWorldLazy(Generic[T], Immutable, metaclass=ImmutableGenericMeta):
    __slots__ = ('__type',)
    __type: Type[T]

    def __call__(self, __dependency: Hashable = None) -> LazyDependency[T]:
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
