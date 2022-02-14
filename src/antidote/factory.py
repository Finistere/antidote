from __future__ import annotations

import inspect
from typing import (Callable, cast, FrozenSet, Iterable, Optional, overload, TypeVar,
                    Union)

from typing_extensions import final, get_type_hints

from ._factory import FactoryMeta, FactoryWrapper
from ._internal import API
from ._internal.utils import Copy, FinalImmutable
from ._providers import FactoryProvider
from ._utils import validated_parameters
from .core import inject, Scope, Wiring, WithWiringMixin
from .core.exceptions import DoubleInjectionError
from .core.injection import InjectedCallable
from .utils import validated_scope

T = TypeVar('T')


@API.deprecated
class Factory(metaclass=FactoryMeta, abstract=True):
    """
    .. deprecated:: 1.1
        Use :py:func:`~.factory.factory` instead.

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
        .. deprecated:: 1.1

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
                     singleton: Optional[bool] = None,
                     scope: Optional[Scope] = Scope.sentinel(),
                     parameters: Optional[Iterable[str]] = None):
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
                 ) -> Factory.Conf:
            """
            .. deprecated:: 1.1

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
def factory(f: T,
            *,
            singleton: Optional[bool] = None,
            scope: Optional[Scope] = Scope.sentinel(),
            wiring: Optional[Wiring] = Wiring()
            ) -> T:
    ...  # pragma: no cover


@overload
def factory(*,
            singleton: Optional[bool] = None,
            scope: Optional[Scope] = Scope.sentinel(),
            wiring: Optional[Wiring] = Wiring()
            ) -> Callable[[T], T]:
    ...  # pragma: no cover


@API.public
def factory(f: Optional[T] = None,
            *,
            singleton: Optional[bool] = None,
            scope: Optional[Scope] = Scope.sentinel(),
            wiring: Optional[Wiring] = Wiring()
            ) -> Union[Callable[[T], T], T]:
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

    Now to retrieve the dependency:

    .. doctest:: factory

        >>> from antidote import inject, world
        >>> @inject
        ... def f(db: Database = inject.me(source=load_db)) -> Database:
        ...     return db
        >>> f() is world.get(Database, source=load_db)
        True

    :py:func:`.inject` supports two other alternatives:

    .. doctest:: factory

        >>> from typing import Annotated
        >>> from antidote import From, Get
        >>> @inject
        ... def f(db: Annotated[Database, From(load_db)]) -> Database:
        ...     return db
        >>> @inject({'db': Get(Database, source=load_db)})
        ... def f(db: Database) -> Database:
        ...     return db

    It's also possible to have a stateful factory using a class. The class will be instantiated
    only once.

    .. doctest:: factory

        >>> @factory
        ... class DatabaseFactory:
        ...     def __call__(self) -> Database:
        ...         return Database()


    Args:
        f: Factory function or class which builds the dependency.
        singleton: Whether the returned dependency is a singleton or not. If so,
            the factory will be called at most once and the result re-used. Mutually
            exclusive with :code:`scope`. Defaults to :py:obj:`True`.
        scope: Scope of the returned dependency. Mutually exclusive with
            :code:`singleton`. The scope defines if and how long the returned dependency
            will be cached. See :py:class:`~.core.container.Scope`. Defaults to
            :py:meth:`~.core.container.Scope.singleton`.
        wiring: :py:class:`.Wiring` to be used on the class. By defaults will apply
            a simple :py:func:`.inject` on all methods, so only annotated type hints are
            taken into account. Can be deactivated by specifying :py:obj:`None`. If the
            factory is a function, it'll only be injected if not :py:obj:`None`.

    Returns:
        The factory or the decorator.

    """
    scope = validated_scope(scope, singleton, default=Scope.singleton())
    if wiring is not None and not isinstance(wiring, Wiring):
        raise TypeError(f"wiring must be a Wiring or None, not a {type(wiring)!r}")

    @inject
    def register_factory(func: T,
                         factory_provider: FactoryProvider = inject.me()
                         ) -> T:
        from .service import service

        if callable(func) and (inspect.isfunction(func) or isinstance(func, InjectedCallable)):
            output: object = get_type_hints(func).get('return')  # type: ignore

            if output is None:
                raise ValueError("A return type hint is necessary. "
                                 "It is used a the dependency.")
            if not (isinstance(output, type) and inspect.isclass(output)):
                raise TypeError(f"The return type hint is expected to be a class, "
                                f"not {type(output)}.")

            if wiring is not None:
                try:
                    func = inject(func, dependencies=wiring.dependencies)  # type: ignore
                except DoubleInjectionError:
                    pass

            # TODO: Remove legacy wrapper for the 'dependency @ factory' notation
            func = cast(T, FactoryWrapper(wrapped=cast(Callable[..., object], func), output=output))
            factory_provider.register(factory=cast(Callable[..., object], func),
                                      scope=scope,
                                      output=output)
        elif isinstance(func, type) and inspect.isclass(func):
            output = get_type_hints(func.__call__).get('return')
            if output is None:
                raise ValueError("A return type hint is necessary. "
                                 "It is used a the dependency.")
            if not (isinstance(output, type) and inspect.isclass(output)):
                raise TypeError(f"The return type hint is expected to be a class, "
                                f"not {type(output)}.")

            func = service(func, singleton=True, wiring=wiring)  # type: ignore

            factory_provider.register(
                output=output,
                scope=scope,
                factory_dependency=func
            )
        else:
            raise TypeError(f"Factory must be either a class or a function, not a {type(func)}")

        return func

    return f and register_factory(f) or register_factory
