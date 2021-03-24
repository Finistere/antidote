import inspect
from typing import (Callable, FrozenSet, Iterable, Optional, TypeVar, Union, cast,
                    overload)

from ._compatibility.typing import Protocol, final, get_type_hints
from ._factory import FactoryMeta, FactoryWrapper
from ._internal import API
from ._internal.utils import Copy, FinalImmutable
from ._internal.wrapper import is_wrapper
from ._providers import FactoryProvider
from ._utils import validated_parameters
from .core import Provide, Scope, Wiring, WithWiringMixin, inject
from .core.exceptions import DoubleInjectionError
from .utils import validated_scope

F = TypeVar('F', bound=Callable[..., object])


@API.private
class FactoryProtocol(Protocol[F]):
    """
    :meta private:
    """

    def __rmatmul__(self, klass: type) -> object:
        pass  # pragma: no cover

    __call__: F


@API.public
class Factory(metaclass=FactoryMeta, abstract=True):
    """
    Defines sublcass as a factory to Antidote. The provided dependency is defined through
    the type annotation of :py:meth:`.__call__`:

    .. doctest:: factory_class

        >>> from antidote import Factory
        >>> class Database:
        ...     pass
        ...
        >>> class DatabaseLoader(Factory):
        ...     def __call__(self) -> Database:
        ...         return Database()

    To retrieve the dependency from Antidote you need to use a specific syntax
    :code:`dependency @ factory` as presented in the following examples. The goal of it is
    twofold:

    - Ensure that the factory is loaded whenever you require the dependency.
    - Better maintainability as you know *where* the dependency comes from.

    .. doctest:: factory_class

        >>> from antidote import world, inject
        >>> world.get(Database @ DatabaseLoader)  # treated as `object` by Mypy
        <Database ...>
        >>> # With Mypy casting
        ... world.get[Database](Database @ DatabaseLoader)
        <Database ...>
        >>> # Concise Mypy casting
        ... world.get[Database] @ DatabaseLoader
        <Database ...>
        >>> @inject([Database @ DatabaseLoader])
        ... def f(db: Database):
        ...     pass

    Or with annotated type hints:

    .. doctest:: factory_class

        >>> from typing import Annotated
        ... # from typing_extensions import Annotated # Python < 3.9
        >>> from antidote import From
        >>> @inject
        ... def f(db: Annotated[Database, From(DatabaseLoader)]):
        ...     pass

    .. note::

        If you only need a simple function, consider using :py:func:`.factory` instead. It
        behaves the same way as above

    All methods are injected by default and the factory returns a singleton by default.
    All of this can be configured with :py:attr:`.__antidote__`:

    .. doctest:: factory_class

        >>> # Singleton by default
        ... world.get[Database] @ DatabaseLoader is world.get[Database] @ DatabaseLoader
        True
        >>> class Session:
        ...     pass
        >>> # The factory will be called anew each time a `Session` is needed. But the
        ... # factory itself, `SessionFactory`, will only be created once.
        ... class SessionFactory(Factory):
        ...     __antidote__ = Factory.Conf(singleton=False)
        ...
        ...     def __init__(self, db: Annotated[Database, From(DatabaseLoader)]):
        ...         self.db = db
        ...
        ...     def __call__(self) -> Session:
        ...         return Session()
        ...
        >>> world.get[Session] @ SessionFactory is world.get[Session] @ SessionFactory
        False

    You may also parameterize the service. Parameters will be passed on to
    :code:`__call__()`:

    .. doctest:: factory_class

        >>> class Database:
        ...     def __init__(self, host: str):
        ...         self.host = host
        ...
        >>> class DatabaseFactory(Factory):
        ...     __antidote__ = Factory.Conf(parameters=['host'])
        ...
        ...     def __call__(self, host: str) -> Database:
        ...         return Database(host)
        ...
        ...     @classmethod
        ...     def hosted(cls, host: str) -> object:
        ...          return cls.parameterized(host=host)
        ...
        >>> test_db = world.get[Database] @ DatabaseFactory.hosted('test')
        >>> test_db.host
        'test'
        >>> # The factory returns a singleton so our test_session will also be one
        ... world.get[Database] @ DatabaseFactory.hosted('test') is test_db
        True

    """

    @final
    class Conf(FinalImmutable, WithWiringMixin):
        """
        Immutable factory configuration. To change parameters on a existing instance, use
        either method :py:meth:`.copy` or
        :py:meth:`.core.wiring.WithWiringMixin.with_wiring`.
        """
        __slots__ = ('wiring', 'scope', 'parameters')
        wiring: Optional[Wiring]
        scope: Optional[Scope]
        parameters: Optional[FrozenSet[str]]

        @property
        def singleton(self) -> bool:
            return self.scope is Scope.singleton()

        def __init__(self,
                     *,
                     wiring: Optional[Wiring] = Wiring(),
                     singleton: bool = None,
                     scope: Optional[Scope] = Scope.sentinel(),
                     parameters: Iterable[str] = None):
            """

            Args:
                wiring: Wiring to be applied on the factory. By default only
                    :code:`__init__()` and :code:`__call__()` will be wired. To deactivate
                    any wiring at all use :py:obj:`None`.
                singleton: Whether the returned dependency  is a singleton or not. If yes,
                    the factory will be called at most once and the result re-used.
                    Mutually exclusive with :code:`scope`. Defaults to :py:obj:`True`
                scope: Scope of the returned dependency. Mutually exclusive with
                    :code:`singleton`. The scope defines if and how long the returned
                    dependency will be cached. See :py:class:`~.core.container.Scope`.
                    Defaults to :py:meth:`~.core.container.Scope.singleton`.
            """
            if not (wiring is None or isinstance(wiring, Wiring)):
                raise TypeError(f"wiring must be a Wiring or None, "
                                f"not {type(wiring)}")

            super().__init__(wiring=wiring,
                             scope=validated_scope(scope,
                                                   singleton,
                                                   default=Scope.singleton()),
                             parameters=validated_parameters(parameters))

        def copy(self,
                 *,
                 wiring: Union[Optional[Wiring], Copy] = Copy.IDENTICAL,
                 singleton: Union[bool, Copy] = Copy.IDENTICAL,
                 scope: Union[Optional[Scope], Copy] = Copy.IDENTICAL,
                 parameters: Union[Optional[Iterable[str]], Copy] = Copy.IDENTICAL,
                 ) -> 'Factory.Conf':
            """
            Copies current configuration and overrides only specified arguments.
            Accepts the same arguments as :py:meth:`.__init__`
            """
            if not (singleton is Copy.IDENTICAL or scope is Copy.IDENTICAL):
                raise TypeError("Use either singleton or scope argument, not both.")
            if isinstance(singleton, bool):
                scope = Scope.singleton() if singleton else None
            return Copy.immutable(self,
                                  wiring=wiring,
                                  scope=scope,
                                  parameters=parameters)

    __antidote__: Conf = Conf()
    """
    Configuration of the factory. Defaults to wire :py:meth:`.__init__` and
    :py:meth:`.__call__`.
    """


@overload
def factory(f: F,  # noqa: E704  # pragma: no cover
            *,
            singleton: bool = None,
            scope: Optional[Scope] = Scope.sentinel(),
            ) -> FactoryProtocol[F]: ...


@overload
def factory(*,  # noqa: E704  # pragma: no cover
            singleton: bool = None,
            scope: Optional[Scope] = Scope.sentinel(),
            ) -> Callable[[F], FactoryProtocol[F]]: ...


@API.public
def factory(f: F = None,
            *,
            singleton: bool = None,
            scope: Optional[Scope] = Scope.sentinel(),
            ) -> Union[FactoryProtocol[F], Callable[[F], FactoryProtocol[F]]]:
    """
    Registers a factory which provides as single dependency, defined through the return
    type annotation.

    .. doctest:: factory

        >>> from antidote import factory
        >>> class Database:
        ...     pass
        >>> @factory
        ... def load_db() -> Database:
        ...     return Database()

    To retrieve the dependency from Antidote you need to use a specific syntax
    :code:`dependency @ factory` as presented in the following examples. The goal of it is
    twofold:

    - Ensure that the factory is loaded whenever you require the dependency.
    - Better maintainability as you know *where* the dependency comes from.

    .. doctest:: factory

        >>> from antidote import world, inject
        >>> world.get(Database @ load_db)  # treated as `object` by Mypy
        <Database ...>
        >>> # With Mypy casting
        ... world.get[Database](Database @ load_db)
        <Database ...>
        >>> # Concise Mypy casting
        ... world.get[Database] @ load_db
        <Database ...>
        >>> @inject([Database @ load_db])
        ... def f(db: Database):
        ...     pass

    Or with annotated type hints:

    .. doctest:: factory

        >>> from typing import Annotated
        ... # from typing_extensions import Annotated # Python < 3.9
        >>> from antidote import From
        >>> @inject
        ... def f(db: Annotated[Database, From(load_db)]):
        ...     pass

    The factory returns a singleton by default and is automatically injected, so
    you can use annotated type hints with it:

    .. doctest:: factory

        >>> # Singleton by default
        ... world.get[Database] @ load_db is world.get[Database] @ load_db
        True
        >>> class Session:
        ...     pass
        >>> @factory(singleton=False)
        ... def session_gen(db: Annotated[Database, From(load_db)]) -> Session:
        ...     return Session()
        >>> world.get[Session] @ session_gen is world.get[Session] @ session_gen
        False

    .. note::

        If you need a stateful factory or want to implement a complex one prefer using
        :py:class:`.Factory` instead.

    Args:
        f: Callable which builds the dependency.
        singleton: Whether the returned dependency  is a singleton or not. If yes,
            the factory will be called at most once and the result re-used. Mutually
            exclusive with :code:`scope`. Defaults to :py:obj:`True`.
        scope: Scope of the returned dependency. Mutually exclusive with
            :code:`singleton`. The scope defines if and how long the returned dependency
            will be cached. See :py:class:`~.core.container.Scope`. Defaults to
            :py:meth:`~.core.container.Scope.singleton`.
        tags: Iterable of :py:class:`~.._providers.tag.Tag` applied to the provided
            dependency.

    Returns:
        The factory or the function decorator.

    """
    scope = validated_scope(scope, singleton, default=Scope.singleton())

    @inject
    def register_factory(func: F,
                         factory_provider: Provide[FactoryProvider] = None
                         ) -> FactoryProtocol[F]:
        assert factory_provider is not None

        if not (inspect.isfunction(func)
                or (is_wrapper(func)
                    and inspect.isfunction(func.__wrapped__))):  # type: ignore
            raise TypeError(f"{func} is not a function")

        output = get_type_hints(func).get('return')
        if output is None:
            raise ValueError("A return type hint is necessary. "
                             "It is used a the dependency.")
        if not inspect.isclass(output):
            raise TypeError(f"The return type hint is expected to be a class, "
                            f"not {type(output)}.")

        try:
            func = inject(func)
        except DoubleInjectionError:
            pass

        dependency = factory_provider.register(factory=func,
                                               scope=scope,
                                               output=output)

        return cast(FactoryProtocol[F], FactoryWrapper(func, dependency))

    return f and register_factory(f) or register_factory
