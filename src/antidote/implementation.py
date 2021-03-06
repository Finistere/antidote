import functools
import inspect
from typing import Callable, TypeVar, cast

from ._compatibility.typing import Protocol
from ._implementation import ImplementationWrapper, validate_provided_class
from ._internal import API
from ._internal.wrapper import is_wrapper
from ._providers import IndirectProvider
from .core import Provide, inject
from .core.exceptions import DoubleInjectionError

F = TypeVar('F', bound=Callable[[], object])


@API.private
class ImplementationProtocol(Protocol[F]):
    """
    :meta private:
    """

    def __rmatmul__(self, klass: type) -> object:
        pass  # pragma: no cover

    __call__: F


@API.public
def implementation(interface: type,
                   *,
                   permanent: bool = True
                   ) -> Callable[[F], ImplementationProtocol[F]]:
    """
    Defines which dependency should be retrieved when :code:`interface` is requested.
    Suppose we have to support two different databases and the configuration defines
    which one should be chosen:

    .. doctest:: implementation

        >>> from antidote import Constants, const
        >>> class Config(Constants):
        ...     DB = const('postgres')
        >>> # The interface
        ... class Database:
        ...     pass

    .. doctest:: implementation

        >>> from antidote import Service, factory
        >>> class PostgreSQL(Database, Service):
        ...     pass
        >>> class MySQL(Database):
        ...     pass
        >>> @factory
        ... def build_mysql() -> MySQL:
        ...     return MySQL()

    The decorated function must return the dependency that should be used for
    :code:`Database`. It'll be automatically injected, so you can use annotated type hints
    on it. Furthermore, the chosen implementation is by default permanent. Meaning that
    the decorated function will only be called once, at most.

    .. doctest:: implementation

        >>> from antidote import implementation, Get
        >>> from typing import Annotated
        ... # from typing_extensions import Annotated # Python < 3.9
        >>> @implementation(Database)
        ... def local_db(choice: Annotated[str, Get(Config.DB)]) -> object:
        ...     if choice == 'postgres':
        ...         return PostgreSQL
        ...     else:
        ...         return MySQL @ build_mysql

    To retrieve the actual implementation from Antidote you need to use a specific syntax
    :code:`dependency @ implementation` as presented in the following examples.
    The goal of it is twofold:

    - Ensure that the implementation is loaded whenever you require the interface.
    - Better maintainability as you know *where* the dependenciy comes from.

    .. doctest:: implementation

        >>> from antidote import world, inject
        >>> world.get(Database @ local_db)  # treated as `object` by Mypy
        <PostgreSQL ...>
        >>> # With Mypy casting
        ... world.get[Database](Database @ local_db)
        <PostgreSQL ...>
        >>> # Concise Mypy casting
        ... world.get[Database] @ local_db
        <PostgreSQL ...>
        >>> @inject([Database @ local_db])
        ... def f(db: Database):
        ...     pass

    Or with annotated type hints:

    .. doctest:: implementation

        >>> from typing import Annotated
        ... # from typing_extensions import Annotated # Python < 3.9
        >>> from antidote import From
        >>> @inject
        ... def f(db: Annotated[Database, From(local_db)]):
        ...     pass

    Args:
        interface: Interface for which an implementation will be provided
        permanent: Whether the function should be called each time the interface is needed
            or not. Defaults to :py:obj:`True`.

    Returns:
        The decorated function, unmodified.
    """
    if not isinstance(permanent, bool):
        raise TypeError(f"permanent must be a bool, not {type(permanent)}")
    if not inspect.isclass(interface):
        raise TypeError(f"interface must be a class, not {type(interface)}")

    @inject
    def register(func: F,
                 indirect_provider: Provide[IndirectProvider] = None
                 ) -> ImplementationProtocol[F]:
        assert indirect_provider is not None

        if not (inspect.isfunction(func)
                or (is_wrapper(func)
                    and inspect.isfunction(func.__wrapped__))):  # type: ignore
            raise TypeError(f"{func} is not a function")

        try:
            func = inject(func)
        except DoubleInjectionError:
            pass

        @functools.wraps(func)
        def impl() -> object:
            dep = func()
            validate_provided_class(dep, expected=interface)
            return dep

        dependency = indirect_provider.register_implementation(interface, impl,
                                                               permanent=permanent)
        return cast(ImplementationProtocol[F], ImplementationWrapper(func, dependency))

    return register
