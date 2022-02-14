from __future__ import annotations

from typing import Any, Callable, Optional, Type, TYPE_CHECKING, TypeVar, Union

from .._internal import API
from .._internal.utils import FinalImmutable

if TYPE_CHECKING:
    from .typing import CallableClass, Source

T = TypeVar('T')


@API.private
class Marker:
    pass


@API.private  # See @inject decorator for usage.
class InjectMeMarker(Marker, FinalImmutable):
    __slots__ = ('source',)
    source: Optional[Union[Source[Any], Callable[..., Any], Type[CallableClass[Any]]]]

    def __init__(self,
                 *,
                 source: Optional[Union[
                     Source[Any],
                     Callable[..., Any],
                     Type[CallableClass[Any]]
                 ]]
                 ) -> None:
        super().__init__(source)
