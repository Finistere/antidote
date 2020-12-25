import functools
import inspect
from typing import Callable, cast, Dict, get_type_hints, Hashable, Tuple, Type

from ._internal import API
from ._internal.utils import AbstractMeta, FinalImmutable
from ._providers import FactoryProvider, TagProvider
from ._providers.factory import FactoryDependency
from ._providers.service import Build
from .core import Dependency, inject
from .lazy import LazyCall
from .service import service

_ABSTRACT_FLAG = '__antidote_abstract'


@API.private
class FactoryMeta(AbstractMeta):
    __factory_dependency: FactoryDependency

    def __new__(mcs: 'Type[FactoryMeta]',
                name: str,
                bases: Tuple[type, ...],
                namespace: Dict[str, object],
                **kwargs: object
                ) -> 'FactoryMeta':
        abstract = kwargs.get('abstract')

        if '__call__' not in namespace and not abstract:
            raise TypeError(f"The class {name} must implement __call__()")

        cls = cast(
            FactoryMeta,
            super().__new__(mcs, name, bases, namespace, **kwargs)  # type: ignore
        )
        if not abstract:
            cls.__factory_dependency = _configure_factory(cls)

        return cls

    @API.public
    def __rmatmul__(cls, left_operand: Hashable) -> object:
        assert cls.__factory_dependency is not None
        if left_operand is not cls.__factory_dependency.output:
            raise ValueError(f"Unsupported output {left_operand}")
        return cls.__factory_dependency

    @API.public
    def with_kwargs(cls, **kwargs: object) -> 'PreBuild':
        """
        Creates a new dependency based on the factory which will have the keyword
        arguments provided. If the factory provides a singleton and identical kwargs are
        used, the same instance will be returned by Antidote.

        Args:
            **kwargs: Arguments passed on to the factory.

        Returns:
            Dependency to be retrieved from Antidote.
        """
        assert cls.__factory_dependency is not None
        return PreBuild(cls.__factory_dependency, kwargs)


@API.private
@inject
def _configure_factory(cls: FactoryMeta,
                       factory_provider: FactoryProvider = None,
                       tag_provider: TagProvider = None) -> FactoryDependency:
    from .factory import Factory
    assert factory_provider is not None

    conf = getattr(cls, '__antidote__', None)
    if not isinstance(conf, Factory.Conf):
        raise TypeError(f"Factory configuration (__antidote__) is expected to be "
                        f"a {Factory.Conf}, not a {type(conf)}")

    output = get_type_hints(cls.__call__).get('return')
    if output is None:
        raise ValueError("The return annotation is necessary on __call__."
                         "It is used a the dependency.")
    if not inspect.isclass(output):
        raise TypeError(f"The return annotation is expected to be a class, "
                        f"not {type(output)}.")

    if conf.wiring is not None:
        conf.wiring.wire(cls)

    factory_dependency = factory_provider.register(
        output=output,
        singleton=conf.singleton,
        factory=Dependency(service(cls, singleton=True)
                           if conf.public else
                           LazyCall(cls, singleton=True))
    )

    if conf.tags is not None:
        if tag_provider is None:
            raise RuntimeError("No TagProvider registered, cannot use tags.")
        tag_provider.register(dependency=factory_dependency, tags=conf.tags)

    return factory_dependency


@API.private
class LambdaFactory:
    def __init__(self, wrapped: Callable[..., object],
                 factory_dependency: FactoryDependency) -> None:
        self.__wrapped__ = wrapped
        self.__factory_dependency = factory_dependency
        functools.wraps(wrapped, updated=())(self)

    def __call__(self, *args: object, **kwargs: object) -> object:
        return self.__wrapped__(*args, **kwargs)

    def __rmatmul__(self, left_operand: Hashable) -> object:
        if left_operand is not self.__factory_dependency.output:
            raise ValueError(f"Unsupported output {left_operand}")
        return self.__factory_dependency

    def with_kwargs(self, **kwargs: object) -> 'PreBuild':
        return PreBuild(self.__factory_dependency, kwargs)

    def __getattr__(self, item: str) -> object:
        return getattr(self.__wrapped__, item)


@API.private
class PreBuild(FinalImmutable):
    __slots__ = ('_factory_dependency', '_kwargs')
    _factory_dependency: FactoryDependency
    _kwargs: Dict[str, object]

    def __init__(self, factory_dependency: FactoryDependency,
                 kwargs: Dict[str, object]) -> None:
        if not kwargs:
            raise ValueError("When calling with_kwargs(), "
                             "at least one argument must be provided.")
        super().__init__(_factory_dependency=factory_dependency, _kwargs=kwargs)

    def __rmatmul__(self, left_operand: Hashable) -> object:
        if left_operand is not self._factory_dependency.output:
            raise ValueError(f"Unsupported output {left_operand}")
        return Build(self._factory_dependency, self._kwargs)
