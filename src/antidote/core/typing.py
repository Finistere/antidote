# pyright: reportInvalidTypeVarUse=false
from __future__ import annotations

from typing import Any, Generic, Type, TypeVar

from typing_extensions import Protocol, runtime_checkable

from .marker import Marker
from .._internal import API

Tct = TypeVar("Tct", contravariant=True)
Tco = TypeVar("Tco", covariant=True)
T = TypeVar("T")


@API.private
@runtime_checkable
class Source(Protocol[Tct]):
    def __antidote_dependency__(self, dependency: Type[Tct]) -> object:
        """
        The input type is not guaranteed. You MUST check the type. Raise an error if this
        source cannot provide the specified target.
        """


@API.private
class CallableClass(Protocol[Tco]):
    def __call__(self, *args: Any, **kwargs: Any) -> Tco:
        ...


@API.private
class Dependency(Generic[Tco], Marker):
    pass
