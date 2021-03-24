from typing import Callable, FrozenSet, Iterable, Optional, TypeVar, Union, cast, overload

from ._compatibility.typing import final
from ._internal import API
from ._internal.utils import Copy, FinalImmutable
from ._service import ServiceMeta
from ._utils import validated_parameters
from .core import Scope, Wiring, WithWiringMixin
from .core.exceptions import DuplicateDependencyError
from .utils import validated_scope

C = TypeVar('C', bound=type)


@API.public
class Service(metaclass=ServiceMeta, abstract=True):
    """
    Defines subclasses as services:

    .. doctest:: service_class

        >>> from antidote import Service, world, inject
        >>> class Database(Service):
        ...     pass

    The service can then be retrieved by its class:

    .. doctest:: service_class

        >>> world.get(Database)  # treated as `object` by Mypy
        <Database ...>
        >>> # With Mypy casting
        ... world.get[Database]()
        <Database ...>
        >>> @inject([Database])
        ... def f(db: Database):
        ...     pass

    Or with annotated type hints:

    .. doctest:: service_class

        >>> from antidote import Provide
        >>> @inject
        ... def f(db: Provide[Database]):
        ...     pass

    All methods are injected by default and the service itself is a singleton.
    All of this can be configured with :py:attr:`.__antidote__`:

    .. doctest:: service_class

        >>> # Singleton by default
        ... world.get[Database]() is world.get[Database]()
        True
        >>> class Session(Service):
        ...     __antidote__ = Service.Conf(singleton=False)
        ...
        ...     def __init__(self, db: Provide[Database]):
        ...         self.db = db
        ...
        >>> world.get[Session]() is world.get[Session]()
        False

    You may also parameterize the service. Parameters will be passed on to
    :code:`__init__()`:

    .. doctest:: service_class

        >>> class Database(Service):
        ...     __antidote__ = Service.Conf(parameters=['host'])
        ...
        ...     def __init__(self, host: str):
        ...         self.host = host
        ...
        ...     @classmethod
        ...     def hosted(cls, host: str) -> object:
        ...         return cls.parameterized(host=host)
        ...
        >>> test_db = world.get[Database](Database.hosted('test'))
        >>> test_db.host
        'test'
        >>> # The factory returns a singleton so our test_session will also be one
        ... world.get[Database](Database.hosted('test')) is test_db
        True

    """

    @final
    class Conf(FinalImmutable, WithWiringMixin):
        """
        Immutable service configuration. To change parameters on a existing instance, use
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
                wiring: Wiring to be applied on the service. By default only
                    :code:`__init__()` will be wired. Unless :py:attr:`.factory` is class
                    method name, in which case only the latter would be wired. To
                    deactivate any wiring at all use :py:obj:`None`.
                singleton: Whether the service is a singleton or not. A singleton is
                    instantiated only once. Mutually exclusive with :code:`scope`.
                    Defaults to :py:obj:`True`
                scope: Scope of the service. Mutually exclusive with :code:`singleton`.
                    The scope defines if and how long the service will be cached. See
                    :py:class:`~.core.container.Scope`. Defaults to
                    :py:meth:`~.core.container.Scope.singleton`.
            """
            if not (wiring is None or isinstance(wiring, Wiring)):
                raise TypeError(f"wiring must be a Wiring or None, not {type(wiring)}")

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
                 ) -> 'Service.Conf':
            """
            Copies current configuration and overrides only specified arguments.
            Accepts the same arguments as :py:meth:`.__init__`
            """
            if not (singleton is Copy.IDENTICAL or scope is Copy.IDENTICAL):
                raise TypeError("Use either singleton or scope argument, not both.")
            if isinstance(singleton, bool):
                scope = Scope.singleton() if singleton else None
            return Copy.immutable(self, wiring=wiring, scope=scope, parameters=parameters)

    __antidote__: Conf = Conf()
    """
    Configuration of the service. Defaults to wire :py:meth:`.__init__`.
    """


@overload
def service(klass: C,  # noqa: E704  # pragma: no cover
            *,
            singleton: bool = None,
            scope: Optional[Scope] = Scope.sentinel(),
            ) -> C: ...


@overload
def service(*,  # noqa: E704  # pragma: no cover
            singleton: bool = None,
            scope: Optional[Scope] = Scope.sentinel(),
            ) -> Callable[[C], C]: ...


@API.experimental
def service(klass: C = None,
            *,
            singleton: bool = None,
            scope: Optional[Scope] = Scope.sentinel()
            ) -> Union[C, Callable[[C], C]]:
    """
    Defines the decorated class as a service. To be used when you cannot inherit
    :py:class:`.Service`

    .. doctest:: register

        >>> from antidote import service
        >>> @service
        ... class CannotInheritService:
        ...     pass

    .. note::

        If your wish to declare to register an external class to Antidote, prefer using
        a factory with either :py:class:`~.factory.Factory` or
        :py:func:`~.factory.factory`.

    Args:
        klass: Class to register as a dependency. It will be instantiated  only when
            requested.
        singleton: Whether the service is a singleton or not. A singleton is
            instantiated only once. Mutually exclusive with :code:`scope`.
            Defaults to :py:obj:`True`
        scope: Scope of the service. Mutually exclusive with :code:`singleton`.
            The scope defines if and how long the service will be cached. See
            :py:class:`~.core.container.Scope`. Defaults to
            :py:meth:`~.core.container.Scope.singleton`.

    Returns:
        The decorated class, unmodified, if specified or the class decorator.

    """
    scope = validated_scope(scope, singleton, default=Scope.singleton())

    def reg(cls: C) -> C:
        from ._service import _configure_service

        if issubclass(cls, Service):
            raise DuplicateDependencyError(f"{cls} is already defined as a dependency "
                                           f"by inheriting {Service}")

        _configure_service(cls, conf=Service.Conf(wiring=None, scope=scope))

        return cast(C, cls)

    return klass and reg(klass) or reg
