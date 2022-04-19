from __future__ import annotations

import functools
import inspect
from dataclasses import dataclass
from typing import Any, Callable, cast, Generic, Tuple, TypeVar

from typing_extensions import final, ParamSpec, Protocol

from ._provider import LazyFunction
from ..._internal import API
from ...core import Scope

__all__ = ['DependencyKey', 'LazyWrapperWithoutScope', 'LazyWrapper']

T = TypeVar('T')
P = ParamSpec('P')
Tco = TypeVar('Tco', covariant=True)


# See https://github.com/python/mypy/issues/6910
# API.private
class Function(Protocol[P, Tco]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Tco:
        ...


@API.private
@final
class LazyWrapperWithoutScope(Generic[P, T]):
    """placeholder to avoid dataclass using __signature__"""
    __wrapped__: Function[P, T]
    __signature__: inspect.Signature

    def __init__(self, *, func: Callable[P, T]) -> None:
        self.__wrapped__ = func
        self.__signature__ = inspect.signature(func)
        functools.wraps(func)(self)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        if args or kwargs:
            bound = self.__signature__.bind(*args, **kwargs)
            args = cast(Any, bound.args)
            kwargs = cast(Any, bound.kwargs)
        dependency = LazyFunction.of(func=self.__wrapped__,
                                     args=cast(Any, args),
                                     kwargs=cast(Any, kwargs),
                                     scope=None)
        return cast(T, dependency)

    def call(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.__wrapped__(*args, **kwargs)


@API.private
@final
class LazyWrapper(Generic[P, T]):
    """placeholder to avoid dataclass using __signature__"""
    __wrapped__: Function[P, T]
    __scope: Scope
    __signature__: inspect.Signature
    __dependency_cache: dict[DependencyKey, object]

    def __init__(self, *, func: Callable[P, T], scope: Scope) -> None:
        self.__wrapped__ = func
        self.__signature__ = inspect.signature(func)
        self.__scope = scope
        self.__dependency_cache = dict()
        functools.wraps(func)(self)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        if not args and not kwargs:
            key = _empty_key
        else:
            bound = self.__signature__.bind(*args, **kwargs)
            key = DependencyKey.of(bound.args, bound.kwargs)
            args = cast(Any, bound.args)
            kwargs = cast(Any, bound.kwargs)
        try:
            dependency = self.__dependency_cache[key]
        except KeyError:
            lazy = LazyFunction.of(func=self.__wrapped__,
                                   args=cast(Any, args),
                                   kwargs=cast(Any, kwargs),
                                   scope=self.__scope)
            dependency = self.__dependency_cache.setdefault(key, lazy)
        return cast(T, dependency)

    def call(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.__wrapped__(*args, **kwargs)


@API.private
@final
@dataclass(frozen=True)
class DependencyKey:
    __slots__ = ('args', 'kwargs', 'hash')
    args: tuple[object, ...]
    kwargs: dict[str, object]
    hash: int

    @classmethod
    def of(cls, args: tuple[object, ...], kwargs: dict[str, object]) -> DependencyKey:
        # Ensuring a pre-computed hash is always created and as precise as possible.
        args = args or _empty_tuple
        kwargs = kwargs or _empty_dict
        return cls(args=args, kwargs=kwargs, hash=hash((args, tuple(sorted(kwargs.items())))))

    def __hash__(self) -> int:
        return self.hash

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, DependencyKey)
                and self.hash == other.hash
                and (self.args is other.args
                     or self.args == other.args)
                and (self.kwargs is other.kwargs
                     or self.kwargs == other.kwargs))


# For speed and space efficiency
_empty_tuple: tuple[object, ...] = cast(Tuple[object, ...], tuple())
_empty_dict: dict[str, object] = dict()
_empty_key = DependencyKey.of(_empty_tuple, _empty_dict)
