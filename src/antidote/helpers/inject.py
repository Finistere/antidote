from typing import (Callable, Iterable, overload, TypeVar, Union)

from .._internal.utils import API
from ..core import DEPENDENCIES_TYPE, raw_inject

F = TypeVar('F', Callable, staticmethod, classmethod)


@overload
def inject(func: F,  # noqa: E704  # pragma: no cover
           *,
           dependencies: DEPENDENCIES_TYPE = None,
           use_names: Union[bool, Iterable[str]] = None,
           use_type_hints: Union[bool, Iterable[str]] = None
           ) -> F: ...


@overload
def inject(*,  # noqa: E704  # pragma: no cover
           dependencies: DEPENDENCIES_TYPE = None,
           use_names: Union[bool, Iterable[str]] = None,
           use_type_hints: Union[bool, Iterable[str]] = None
           ) -> Callable[[F], F]: ...


@API.public
def inject(func=None,
           *,
           dependencies: DEPENDENCIES_TYPE = None,
           use_names: Union[bool, Iterable[str]] = None,
           use_type_hints: Union[bool, Iterable[str]] = None
           ):
    return raw_inject(func,
                      dependencies=dependencies,
                      use_names=use_names,
                      use_type_hints=use_type_hints)
