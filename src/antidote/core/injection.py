from __future__ import annotations

import collections.abc as c_abc
import inspect
import warnings
from typing import (Any, Callable, Generic, Hashable, Iterable, Mapping, Optional,
                    overload,
                    Sequence, Type, TYPE_CHECKING, TypeVar, Union)

from typing_extensions import final, TypeAlias

from .annotations import Get
from .marker import InjectMeMarker
from .._internal import API
from .._internal.utils import FinalImmutable
from .._internal.utils.meta import Singleton

if TYPE_CHECKING:
    from .typing import CallableClass, Source

F = TypeVar('F', bound=Callable[..., Any])
T = TypeVar('T')
AnyF: TypeAlias = 'Union[Callable[..., Any], staticmethod[Any], classmethod[Any]]'


@API.deprecated
@final
class Arg(FinalImmutable):
    """
    .. deprecated:: 1.1

        Deprecated as specifying a function to :py:func:`~.injection.inject` is deprecated

    Represents an argument (name and type hint) if you need a very custom injection
    logic.
    """
    __slots__ = ('name', 'type_hint', 'type_hint_with_extras')
    name: str
    """Name of the argument"""
    type_hint: Any
    """Type hint of the argument if any"""
    type_hint_with_extras: Any
    """
    Type hint of the argument if any with include_extras=True, so with annotations.
    """

    def __init__(self, name: str, type_hint: Any, type_hint_with_extras: Any) -> None:
        warnings.warn("Deprecated as specifying a function to @inject is deprecated",
                      DeprecationWarning)
        super().__init__(name, type_hint, type_hint_with_extras)


# API.experimental
DEPENDENCIES_TYPE: TypeAlias = Union[
    None,
    Mapping[str, Hashable],  # {arg_name: dependency, ...}
    Sequence[Optional[Hashable]],  # (dependency for arg 1, ...)
    # API.Deprecated
    Callable[[Arg], Optional[Hashable]],  # arg -> dependency
]
# API.deprecated
AUTO_PROVIDE_TYPE: TypeAlias = Optional[Union[
    bool,  # all class type hints or nothing
    Iterable[type],  # specific list of classes
    Callable[[type], bool]  # Function determining which classes should be auto provided
]]


class InjectedCallableMeta(type):
    def __instancecheck__(self, instance: object) -> bool:
        from .._internal.wrapper import is_wrapper
        return is_wrapper(instance)


class InjectedCallable(Generic[F], metaclass=InjectedCallableMeta):
    __wrapped__: F

    def __call__(self, *args: object, **kwargs: object) -> object:
        ...  # pragma: no cover


@API.private  # Use the singleton instance `inject`, not the class directly.
class Inject(Singleton):
    """
    Use :py:obj:`.inject` directly, this class is not meant to instantiated or
    subclassed.
    """

    @API.public
    def me(self,
           *,
           source: Optional[Union[
               Source[Any],
               Callable[..., Any],
               Type[CallableClass[Any]]
           ]] = None
           ) -> Any:
        """
        Injection Marker specifying that the current type hint should be used as dependency.

        .. doctest:: core_inject_me

            >>> from antidote import inject, service
            >>> @service
            ... class MyService:
            ...     pass
            >>> @inject
            ... def f(s: MyService = inject.me()) -> MyService:
            ...     return s
            >>> f()
            <MyService object at ...>

        It also works with dependency sources such as :py:func:`~.factory.factory` or
        :py:func:`.implementation`:

        .. doctest:: core_inject_me_from

            >>> from antidote import inject, factory
            >>> class Dummy:
            ...     pass
            >>> @factory
            ... def current_dummy() -> Dummy:
            ...     return Dummy()
            >>> @inject
            ... def f(d: Dummy = inject.me(source=current_dummy)) -> Dummy:
            ...     return d
            >>> f()
            <Dummy object at ...>

        When the type hint is :code:`Optional` :py:func:`.inject` won't raise
        :py:exc:`~.exceptions.DependencyNotFoundError` but will provide :py:obj:`None` instead:

        .. doctest:: core_inject_me_optional

            >>> from typing import Optional
            >>> from antidote import inject
            >>> class MyService:
            ...     pass
            >>> @inject
            ... def f(s: Optional[MyService] = inject.me()) -> MyService:
            ...     return s
            >>> f() is None
            True

        """
        return InjectMeMarker(source=source)

    @overload
    def get(self, __dependency: object) -> Any:
        ...  # pragma: no cover

    @overload
    def get(self,
            __dependency: Type[T],
            *,
            source: Union[Source[T], Callable[..., T], Type[CallableClass[T]]]
            ) -> Any:
        ...  # pragma: no cover

    @API.public
    def get(self,
            __dependency: Any,
            *,
            source: Optional[Union[
                Source[Any],
                Callable[..., Any],
                Type[CallableClass[Any]]
            ]] = None
            ) -> Any:
        """
        Injection Marker specifying explicitly which dependency to retrieve.

        .. doctest:: core_inject_get

            >>> from antidote import inject, service
            >>> @service
            ... class MyService:
            ...     pass
            >>> @inject
            ... def f(s = inject.get(MyService)):
            ...     return s
            >>> f()
            <MyService object at ...>

        """
        return Get(__dependency, source=source) if source is not None else Get(__dependency)

    @overload
    def __call__(self,
                 __arg: staticmethod[F],
                 *,
                 dependencies: DEPENDENCIES_TYPE = None,
                 auto_provide: API.Deprecated[AUTO_PROVIDE_TYPE] = None,
                 strict_validation: bool = True,
                 ignore_type_hints: bool = False
                 ) -> staticmethod[F]:
        ...  # pragma: no cover

    @overload
    def __call__(self,
                 __arg: classmethod[F],
                 *,
                 dependencies: DEPENDENCIES_TYPE = None,
                 auto_provide: API.Deprecated[AUTO_PROVIDE_TYPE] = None,
                 strict_validation: bool = True,
                 ignore_type_hints: bool = False
                 ) -> classmethod[F]:
        ...  # pragma: no cover

    @overload
    def __call__(self,
                 __arg: F,
                 *,
                 dependencies: DEPENDENCIES_TYPE = None,
                 auto_provide: API.Deprecated[AUTO_PROVIDE_TYPE] = None,
                 strict_validation: bool = True,
                 ignore_type_hints: bool = False
                 ) -> F:
        ...  # pragma: no cover

    @overload
    def __call__(self,
                 *,
                 dependencies: DEPENDENCIES_TYPE = None,
                 auto_provide: API.Deprecated[AUTO_PROVIDE_TYPE] = None,
                 strict_validation: bool = True,
                 ignore_type_hints: bool = False
                 ) -> Callable[[F], F]:
        ...  # pragma: no cover

    @overload
    def __call__(self,
                 __arg: Sequence[object],
                 *,
                 auto_provide: API.Deprecated[AUTO_PROVIDE_TYPE] = None,
                 strict_validation: bool = True,
                 ignore_type_hints: bool = False
                 ) -> Callable[[F], F]:
        ...  # pragma: no cover

    @overload
    def __call__(self,
                 __arg: Mapping[str, object],
                 *,
                 auto_provide: API.Deprecated[AUTO_PROVIDE_TYPE] = None,
                 strict_validation: bool = True,
                 ignore_type_hints: bool = False
                 ) -> Callable[[F], F]:
        ...  # pragma: no cover

    @API.public
    def __call__(self,
                 __arg: Union[None, AnyF, Sequence[object], Mapping[str, object]] = None,
                 *,
                 dependencies: DEPENDENCIES_TYPE = None,
                 auto_provide: API.Deprecated[AUTO_PROVIDE_TYPE] = None,
                 strict_validation: bool = True,
                 ignore_type_hints: bool = False
                 ) -> AnyF:
        """
        Inject the dependencies into the function lazily, they are only retrieved
        upon execution. As several options can apply to the same argument, the priority is
        defined as:

        1. Markers :code:`inject.me`... / Annotated type hints (PEP-593)
        2. Dependencies declared explicitly if any declared with :code:`dependencies`.
        3. Deprecated: Class type hints if specified with :code:`auto_provide`.

        .. doctest:: core_inject

            >>> from antidote import inject, service, Inject
            >>> @service
            ... class A:
            ...     pass
            >>> @service
            ... class B:
            ...     pass
            >>> @inject
            ... def f(a: A = inject.me()):
            ...     pass # a = world.get(A)
            >>> # PEP-593 annotation
            ... @inject
            ... def f(a: Inject[A]):
            ...     pass # a = world.get(A)
            >>> # All possibilities for dependency argument.
            >>> @inject(dict(b='dependency'))  # shortcut
            ... def f(a, b):
            ...     pass
            >>> @inject([None, 'dependency'])  # shortcut
            ... def f(a, b):
            ...     pass  # a, b = <not injected>, world.get('dependency')

        Args:
            ignore_type_hints:
            __arg: Callable to be wrapped. Can also be used on static methods or class
                methods. May also be sequence of dependencies or mapping from argument
                name to dependencies.
            dependencies:
                Explicit definition of the dependencies which overrides :code:`auto_provide`.
                Defaults to :py:obj:`None`. Can be one of:

                - Mapping from argument name to its dependency
                - Sequence of dependencies which will be mapped with the position
                  of the arguments. :py:obj:`None` can be used as a placeholder.

                .. deprecated:: 1.1
                    Specifying a callable is deprecated. The Callable receives
                    :py:class:`~.Arg` as arguments and should return the matching
                    dependency. :py:obj:`None` should be used for arguments without dependency.

            auto_provide:
                .. deprecated:: 1.1

                Whether or not class type hints should be used as the arguments
                dependency. Only classes are taken into account and it works with
                :py:class:`~typing.Optional`. An iterable of classes  may also be supplied
                to activate this feature only for those. A function may also be provided, in
                which case it'll be called to determine whether the class type hint ca be
                provided or not. Defaults to :code:`False`.
            strict_validation: Whether arguments should be strictly validated given the
                decorated function's argumnet. For example, a key in the dependencies dict
                that does not match any argument would raise error. Defaults to
                :py:obj:`True`.

        Returns:
            The decorator to be applied or the injected function if the
            argument :code:`func` was supplied.

        """
        from ._injection import raw_inject

        if isinstance(__arg, (c_abc.Sequence, c_abc.Mapping)):
            if isinstance(__arg, str):
                raise TypeError("First argument must be an sequence/mapping of dependencies "
                                "or the function to be wrapped, not a string.")
            if dependencies is not None:
                raise TypeError("dependencies must be None if a sequence/mapping of "
                                "dependencies is provided as first argument.")
            dependencies = __arg
            __arg = None

        if callable(dependencies):
            warnings.warn("""
            Passing a callable to dependencies is deprecated.
            If you rely on this behavior, wrap @inject instead.
            """, DeprecationWarning)

        if auto_provide is not None:
            warnings.warn("""
            Using auto_provide is deprecated.
            If you rely on this behavior, wrap @inject instead.
            """, DeprecationWarning)

        def decorate(f: AnyF) -> AnyF:
            return raw_inject(
                f,
                dependencies=dependencies,
                auto_provide=auto_provide if auto_provide is not None else False,
                strict_validation=strict_validation,
                ignore_type_hints=ignore_type_hints
            )

        return __arg and decorate(__arg) or decorate


inject = Inject()
inject.__doc__ = \
    """
    Singleton instance of :py:class:`~.core.injection.Inject`
    """


@API.public  # Function will be kept in sync with @inject, so you may use it.
def validate_injection(dependencies: DEPENDENCIES_TYPE = None,
                       auto_provide: API.Deprecated[AUTO_PROVIDE_TYPE] = None) -> None:
    """
    Validates that injection parameters are valid. If not, an error is raised.

    .. doctest:: core_injection_validate_injection

        >>> from antidote.utils import validate_injection
        >>> validate_injection(dependencies={'name': object()})
        >>> validate_injection(dependencies=object())
        Traceback (most recent call last):
          File "<stdin>", line 1, in ?
        TypeError: ...


    Args:
        dependencies: As defined by :py:func:`~.injection.inject`
        auto_provide:
            .. deprecated:: 1.1

            As defined by :py:func:`~.injection.inject`
    """

    if auto_provide is not None:
        warnings.warn("Using auto_provide is deprecated.", DeprecationWarning)

    if not (dependencies is None
            or (isinstance(dependencies, (c_abc.Sequence, c_abc.Mapping))
                and not isinstance(dependencies, str))
            or callable(dependencies)):
        raise TypeError(
            f"dependencies can be None, a mapping of arguments names to dependencies, "
            f"a sequence of dependencies, a function, "
            f"not a {type(dependencies)!r}"
        )
    if isinstance(dependencies, c_abc.Mapping):
        if not all(isinstance(k, str) for k in dependencies.keys()):
            raise TypeError("Dependencies keys must be argument names (str)")

    if isinstance(auto_provide, str) \
            or not (auto_provide is None
                    or callable(auto_provide)
                    or isinstance(auto_provide, (bool, c_abc.Iterable))):
        raise TypeError(
            f"auto_provide must be either a boolean or an iterable of classes, "
            f"not {type(auto_provide)!r}.")

    # If we can iterate over it safely
    if isinstance(auto_provide, (list, set, tuple, frozenset)):
        for cls in auto_provide:
            if not (isinstance(cls, type) and inspect.isclass(cls)):
                raise TypeError(f"auto_provide must be a boolean or an iterable of "
                                f"classes, but contains {cls!r} which is not a class.")
