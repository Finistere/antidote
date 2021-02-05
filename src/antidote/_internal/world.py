"""
Utilities used by world, mostly for syntactic sugar.
"""
from typing import (Any, Generic, Hashable, TYPE_CHECKING, Type, TypeVar, Union,
                    cast)

from . import API
from .state import current_container
from .utils import Default
from .utils.immutable import Immutable, ImmutableGenericMeta
from .utils.meta import FinalMeta
from .._compatibility.typing import Protocol, final
from ..core._annotations import extract_annotated_dependency
from ..core.container import RawContainer
from ..core.exceptions import DependencyNotFoundError
from ..core.utils import LazyDependency

T = TypeVar('T')

if TYPE_CHECKING:
    pass


@API.private
class SupportsRMatmul(Protocol):
    def __rmatmul__(self, type_hint: object) -> Hashable:
        pass  # pragma: no cover


@API.private
@final
class WorldGet(metaclass=FinalMeta):
    def __call__(self, __dependency: Hashable, *, default: Any = Default.sentinel) -> Any:
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
    __slots__ = ('__tpe',)
    __tpe: Type[T]

    def __call__(self,
                 __dependency: Hashable = None,
                 *,
                 default: Union[T, Default] = Default.sentinel) -> T:
        if __dependency is None:
            dependency: object = self.__tpe
        else:
            dependency = extract_annotated_dependency(__dependency)
        try:
            return cast(T, current_container().get(dependency))
        except DependencyNotFoundError:
            if default is not Default.sentinel:
                return default
            raise

    def __matmul__(self, other: SupportsRMatmul) -> T:
        return self.__call__(self.__tpe @ other)


@API.private
@final
class WorldLazy(metaclass=FinalMeta):
    def __call__(self, __dependency: Hashable) -> LazyDependency[Any]:
        return LazyDependency(__dependency)

    def __getitem__(self, tpe: Type[T]) -> 'TypedWorldLazy[T]':
        return TypedWorldLazy(tpe)


@API.private
@final
class TypedWorldLazy(Generic[T], Immutable, metaclass=ImmutableGenericMeta):
    __slots__ = ('__tpe',)
    __tpe: Type[T]

    def __call__(self, __dependency: Hashable = None) -> LazyDependency[T]:
        return LazyDependency[T](self.__tpe if __dependency is None else __dependency)

    def __matmul__(self, other: SupportsRMatmul) -> LazyDependency[T]:
        return self.__call__(self.__tpe @ other)


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
