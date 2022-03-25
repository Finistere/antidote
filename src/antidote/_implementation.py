import functools
import warnings
from typing import Callable, Generic, Hashable, Type, TypeVar

from typing_extensions import ParamSpec

from ._internal import API
from ._providers.indirect import ImplementationDependency

P = ParamSpec('P')
T = TypeVar('T')


@API.private
class ImplementationWrapper(Generic[P, T]):
    def __init__(self,
                 wrapped: Callable[P, T],
                 implementation_dependency: ImplementationDependency) -> None:
        self.__wrapped__ = wrapped
        self.__implementation_dependency = implementation_dependency
        functools.wraps(wrapped, updated=())(self)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.__wrapped__(*args, **kwargs)

    def __antidote_dependency__(self, target: Type[T]) -> object:
        if target is not self.__implementation_dependency.interface:
            interface = self.__implementation_dependency.interface
            raise ValueError(f"Unsupported interface {target}, "
                             f"expected {interface}")
        return self.__implementation_dependency

    def __rmatmul__(self, klass: type) -> object:
        warnings.warn("Prefer the Get(dependency, source=implementation) notation.",
                      DeprecationWarning)
        if klass is not self.__implementation_dependency.interface:
            interface = self.__implementation_dependency.interface
            raise ValueError(f"Unsupported interface {klass}, "
                             f"expected {interface}")
        return self.__implementation_dependency

    def __getattr__(self, item: str) -> object:
        return getattr(self.__wrapped__, item)


@API.private
def validate_provided_class(dependency: Hashable, *, expected: type) -> None:
    from ._providers.factory import FactoryDependency
    from ._providers.service import Parameterized
    from ._providers.indirect import ImplementationDependency

    cls: object = dependency
    if isinstance(cls, Parameterized):
        cls = cls.wrapped
    if isinstance(cls, FactoryDependency):
        cls = cls.output
    if isinstance(cls, ImplementationDependency):
        cls = cls.interface

    if not isinstance(cls, type):
        raise TypeError(f"{dependency} does not provide any class")

    if not issubclass(cls, expected):
        raise TypeError(f"Expected a subclass of {expected}, not {cls}")
