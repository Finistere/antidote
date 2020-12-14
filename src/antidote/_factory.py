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
    def __rmatmul__(cls, dependency: Hashable) -> object:
        assert cls.__factory_dependency is not None
        if dependency != cls.__factory_dependency.dependency:
            raise ValueError(f"Unsupported dependency {dependency}")
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

    dependency = get_type_hints(cls.__call__).get('return')
    if dependency is None:
        raise ValueError("The return annotation is necessary on __call__."
                         "It is used a the dependency.")
    if not inspect.isclass(dependency):
        raise TypeError(f"The return annotation is expected to be a class, "
                        f"not {type(dependency)}.")

    if conf.wiring is not None:
        conf.wiring.wire(cls)

    factory_id = factory_provider.register(
        dependency=dependency,
        singleton=conf.singleton,
        factory=Dependency(service(cls, singleton=True)
                           if conf.public else
                           LazyCall(cls, singleton=True))
    )

    if conf.tags is not None:
        if tag_provider is None:
            raise RuntimeError("No TagProvider registered, cannot use tags.")
        tag_provider.register(dependency=factory_id, tags=conf.tags)

    return factory_id


@API.private
class LambdaFactory:
    def __init__(self, factory: Callable[..., object],
                 dependency_factory: FactoryDependency) -> None:
        self.__factory = factory
        self.__dependency_factory = dependency_factory
        functools.wraps(factory, updated=())(self)

    def __call__(self, *args: object, **kwargs: object) -> object:
        return self.__factory(*args, **kwargs)

    def __rmatmul__(self, dependency: Hashable) -> object:
        if dependency != self.__dependency_factory.dependency:
            raise ValueError(f"Unsupported dependency {dependency}")
        return self.__dependency_factory

    def with_kwargs(self, **kwargs: object) -> 'PreBuild':
        return PreBuild(self.__dependency_factory, kwargs)


@API.private
class PreBuild(FinalImmutable):
    __slots__ = ('dependency_factory', 'kwargs')
    dependency_factory: FactoryDependency
    kwargs: Dict[str, object]

    def __init__(self, dependency_factory: FactoryDependency,
                 kwargs: Dict[str, object]) -> None:
        if not kwargs:
            raise ValueError("When calling with_kwargs, "
                             "at least one argument must be provided.")
        super().__init__(dependency_factory=dependency_factory, kwargs=kwargs)

    def __rmatmul__(self, dependency: Hashable) -> object:
        if dependency != self.dependency_factory.dependency:
            raise ValueError(f"Unsupported dependency {dependency}")
        return Build(self.dependency_factory, self.kwargs)
