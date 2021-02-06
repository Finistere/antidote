from typing import Callable, Hashable, Optional, TypeVar

from .injection import Arg
from .._compatibility.typing import Annotated, Protocol
from .._internal import API
from .._internal.utils import FinalImmutable


@API.private
class SupportsRMatmul(Protocol):
    def __rmatmul__(self, type_hint: object) -> Hashable:
        pass  # pragma: no cover


T = TypeVar('T')


@API.private
class AntidoteAnnotation:
    """Base class for all Antidote annotation."""


# API.private
INJECT_SENTINEL = AntidoteAnnotation()

# API.public
Provide = Annotated[T, INJECT_SENTINEL]
Provide.__doc__ = """
Annotation specifying that the type hint itself is the dependency:

.. doctest:: core_annotation_provide

    >>> from antidote import Service, world, inject, Provide
    >>> from typing import Annotated
    ... # from typing_extensions import Annotated # Python < 3.9
    >>> class Database(Service):
    ...     pass
    >>> @inject
    ... def load_db(db: Provide[Database]):
    ...     return db
    >>> load_db()
    <Database ...>

"""


@API.public
class Get(FinalImmutable, AntidoteAnnotation):
    """
    Annotation specifying explicitly which dependency to inject.

    .. doctest:: core_annotation_get

        >>> from typing import Annotated
        >>> from antidote import world, inject, Get, Constants, const
        >>> class Config(Constants):
        ...     DB_HOST = const('localhost')
        >>> @inject
        ... def f(host: Annotated[str, Get(Config.DB_HOST)]):
        ...     return host
        >>> f() == world.get(Config.DB_HOST)
        True

    """
    __slots__ = ('dependency',)
    dependency: Hashable

    def __init__(self, __dependency: Hashable) -> None:
        super().__init__(dependency=__dependency)


@API.public
class From(FinalImmutable, AntidoteAnnotation):
    """
    Annotation specifying from where a dependency must be provided. To be used with
    :py:func:`~.antidote.factory`, :py:class:`.Factory` and :py:func:`.implementation`
    typically.

    .. doctest:: core_annotations_from

        >>> from typing import Annotated
        >>> from antidote import factory, world, inject, From
        >>> class Database:
        ...     def __init__(self, host: str):
        ...         self.host = host
        >>> @factory
        ... def build_db(host: str = 'localhost:5432') -> Database:
        ...     return Database(host=host)
        >>> @inject
        ... def f(db: Annotated[Database, From(build_db)]) -> Database:
        ...     return db
        >>> f().host
        'localhost:5432'

    """
    __slots__ = ('source',)
    source: SupportsRMatmul

    def __init__(self, __source: SupportsRMatmul) -> None:
        super().__init__(source=__source)


@API.public
class FromArg(FinalImmutable, AntidoteAnnotation):
    """
    Annotation specifying which dependency should be provided based on the argument. The
    function should accept a single argument of type :py:class:`~..injection.Arg` and
    return either a dependency or :py:obj:`None`.

    .. doctest:: core_annotations_from_arg

        >>> from typing import Annotated, TypeVar
        >>> from antidote import world, inject, FromArg, Constants, const, Arg
        >>> class Config(Constants):
        ...     PORT = const(5432)
        ...
        ...     @classmethod
        ...     def from_arg(cls, arg: Arg):
        ...         return getattr(cls, arg.name.upper())
        ...
        >>> T = TypeVar('T')
        >>> ProvideFromConfig = Annotated[T, FromArg(Config.from_arg)]
        >>> @inject
        ... def f(port: ProvideFromConfig[int]) -> int:
        ...     return port
        >>> f()
        5432
    """
    __slots__ = ('function',)
    function: 'Callable[[Arg], Optional[Hashable]]'

    def __init__(self,
                 __function: 'Callable[[Arg], Optional[Hashable]]'
                 ) -> None:
        if callable(__function):
            super().__init__(function=__function)
        else:
            raise TypeError(f"Expected a function, not {type(__function)}")
