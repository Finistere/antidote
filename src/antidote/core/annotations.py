from __future__ import annotations

import inspect
import warnings
from typing import Any, Callable, Hashable, Optional, overload, Type, TYPE_CHECKING, TypeVar, Union

from typing_extensions import Annotated, get_type_hints, Protocol

from .marker import Marker
from .typing import CallableClass, Source
from .._internal import API
from .._internal.utils import FinalImmutable

if TYPE_CHECKING:
    from .injection import Arg


@API.private
class SupportsRMatmul(Protocol):
    def __rmatmul__(self, type_hint: object) -> Hashable:
        pass  # pragma: no cover


T = TypeVar('T')


@API.private
class AntidoteAnnotation:
    """Base class for all Antidote annotation."""
    __slots__ = ()


# API.private
INJECT_SENTINEL = AntidoteAnnotation()

# API.public
Inject = Annotated[T, INJECT_SENTINEL]
Inject.__doc__ = """
Annotation specifying that the type hint itself is the dependency:

.. doctest:: core_annotation_provide

    >>> from antidote import world, inject, Inject, service
    >>> from typing import Annotated
    ... # from typing_extensions import Annotated # Python < 3.9
    >>> @service
    ... class Database:
    ...     pass
    >>> @inject
    ... def load_db(db: Inject[Database]):
    ...     return db
    >>> load_db()
    <Database ...>

"""

# API.deprecated
Provide = Annotated[T, INJECT_SENTINEL]
Provide.__doc__ = Inject.__doc__


@API.public
class Get(FinalImmutable, AntidoteAnnotation, Marker):
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
    dependency: object

    @overload
    def __init__(self, __dependency: object) -> None:
        ...  # pragma: no cover

    @overload
    def __init__(self,
                 __dependency: Type[T],
                 *,
                 source: Union[Source[T], Callable[..., T], Type[CallableClass[T]]]
                 ) -> None:
        ...  # pragma: no cover

    def __init__(self,
                 __dependency: Any,
                 *,
                 source: Optional[Union[
                     Source[Any],
                     Callable[..., Any],
                     Type[CallableClass[Any]]
                 ]] = None
                 ) -> None:
        from .._providers.factory import FactoryDependency

        if isinstance(__dependency, Get):
            __dependency = __dependency.dependency

        if isinstance(source, Source):
            __dependency = source.__antidote_dependency__(__dependency)
        elif source is not None:
            if isinstance(source, type) and inspect.isclass(source):
                output = get_type_hints(source.__call__).get('return')
            elif callable(source):
                output = get_type_hints(source).get('return')
            else:
                raise TypeError(f"{source} is neither a factory function/class nor a source,"
                                f" but a {type(source)}")

            if not (isinstance(output, type) and inspect.isclass(output)):
                raise TypeError(f"{source} is not a valid factory, it must return a class")

            if not (isinstance(__dependency, type) and inspect.isclass(__dependency)):
                raise TypeError(f"dependency must be a class for a factory, "
                                f"not a {type(__dependency)}")

            if not issubclass(output, __dependency):
                raise TypeError(f"Expected dependency {__dependency} does not match output"
                                f" of the factory {source}")

            __dependency = FactoryDependency(
                factory=source,
                output=__dependency
            )

        super().__init__(__dependency)


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

    def __init__(self,
                 __source: Union[
                     SupportsRMatmul,
                     Source[Any],
                     Callable[..., Any],
                     Type[CallableClass[Any]]]
                 ) -> None:
        super().__init__(source=__source)


@API.deprecated
class FromArg(FinalImmutable, AntidoteAnnotation):
    """
    .. deprecated:: 1.1
        Specifying a callable to :py:func:`.inject` is deprecated, so is this annotation.
        If you rely on this behavior, you'll need to wrap @inject and do the annotation parsing
        yourself.

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
    function: Callable[[Arg], Optional[Hashable]]

    def __init__(self,
                 __function: Callable[[Arg], Optional[Hashable]]
                 ) -> None:
        warnings.warn("Deprecated, @inject won't support this behavior anymore", DeprecationWarning)
        if callable(__function):
            super().__init__(function=__function)
        else:
            raise TypeError(f"Expected a function, not {type(__function)}")
