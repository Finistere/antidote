import functools
import inspect
from typing import Callable, Dict, Hashable, Tuple, Type, cast

from ._compatibility.typing import get_type_hints
from ._internal import API
from ._internal.utils import AbstractMeta, FinalImmutable
from ._providers import FactoryProvider
from ._providers.factory import FactoryDependency
from ._providers.service import Build
from .core import LazyDependency, Provide, inject
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
        if left_operand is not cls.__factory_dependency.output:
            output = cls.__factory_dependency.output
            raise ValueError(f"Unsupported output {left_operand}, expected {output}")
        return cls.__factory_dependency

    @API.public
    def _with_kwargs(cls, **kwargs: object) -> 'PreBuild':
        """
        Creates a new dependency based on the factory with the given arguments. The new
        dependency will have the same scope as the original one.

        The recommended usage is to provide a classmethod exposing only parameters that
        may be changed:

        .. doctest:: service_meta

            >>> from antidote import Factory, world
            >>> class Database:
            ...     def __init__(self, host: str):
            ...         self.host = host
            >>> class DatabaseFactory(Factory):
            ...     def __call__(self, host: str = 'localhost') -> Database:
            ...         return Database(host)
            ...
            ...     @classmethod
            ...     def with_host(cls, host: str) -> object:
            ...         return cls._with_kwargs(host=host)
            >>> db = world.get(Database @ DatabaseFactory.with_host(host='remote'))
            >>> db.host
            'remote'
            >>> # As DatabaseFactory is defined to return a singleton,
            ... # the same is applied:
            ... world.get(Database @ DatabaseFactory.with_host(host='remote')) is db
            True
            >>> # Custom dependencies will NEVER be equal to the default one
            ... world.get(Database @ DatabaseFactory) is db
            False

        Args:
            **kwargs: Arguments passed on to :code:`__call__()`.

        Returns:
            Dependency to be retrieved from Antidote.
        """
        assert cls.__factory_dependency is not None
        return PreBuild(cls.__factory_dependency, kwargs)


@API.private
@inject
def _configure_factory(cls: FactoryMeta,
                       factory_provider: Provide[FactoryProvider] = None
                       ) -> FactoryDependency:
    from .factory import Factory
    assert factory_provider is not None

    conf = getattr(cls, '__antidote__', None)
    if not isinstance(conf, Factory.Conf):
        raise TypeError(f"Factory configuration (__antidote__) is expected to be "
                        f"a {Factory.Conf}, not a {type(conf)}")

    output = get_type_hints(cls.__call__).get('return')
    if output is None:
        raise ValueError("The return type hint is necessary on __call__."
                         "It is used a the dependency.")
    if not inspect.isclass(output):
        raise TypeError(f"The return type hint is expected to be a class, "
                        f"not {type(output)}.")

    if conf.wiring is not None:
        conf.wiring.wire(cls)

    factory_dependency = factory_provider.register(
        output=output,
        scope=conf.scope,
        factory_dependency=service(cls, singleton=True)
    )

    return factory_dependency


@API.private
class FactoryWrapper:
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

    def __getattr__(self, item: str) -> object:
        return getattr(self.__wrapped__, item)


@API.private
class PreBuild(FinalImmutable):
    __slots__ = ('__factory_dependency', '__kwargs')
    __factory_dependency: FactoryDependency
    __kwargs: Dict[str, object]

    def __init__(self, factory_dependency: FactoryDependency,
                 kwargs: Dict[str, object]) -> None:
        if not kwargs:
            raise ValueError("When calling with_kwargs(), "
                             "at least one argument must be provided.")
        super().__init__(factory_dependency, kwargs)

    def __rmatmul__(self, left_operand: Hashable) -> object:
        if left_operand is not self.__factory_dependency.output:
            raise ValueError(f"Unsupported output {left_operand}")
        return Build(self.__factory_dependency, self.__kwargs)
