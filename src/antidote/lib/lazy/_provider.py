from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Hashable, Optional, Tuple

from typing_extensions import final

from ..._internal import API
from ..._internal.utils import debug_repr
from ..._internal.utils.debug import get_injections
from ...core import Container, DependencyDebug, DependencyValue, StatelessProvider
from ...core.container import RawMarker, Scope
from ...core.exceptions import DebugNotAvailableError


@API.private
class Lazy:
    def __antidote_debug_info__(self) -> DependencyDebug:
        raise DebugNotAvailableError()

    def __antidote_provide__(self, container: Container) -> DependencyValue:
        raise NotImplementedError()  # pragma: no cover


@API.private
@dataclass(frozen=True, eq=False)
class LazyFunction(Lazy, RawMarker):
    func: Callable[..., Any]
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]
    scope: Optional[Scope]

    @classmethod
    def of(cls,
           func: Callable[..., Any],
           args: Tuple[Any, ...],
           kwargs: Dict[str, Any],
           scope: Optional[Scope]
           ) -> Lazy:
        return cls(func=func, args=args, kwargs=kwargs, scope=scope)

    def __antidote_debug_repr__(self) -> str:
        out = [f"{debug_repr(self.func)}("]
        for arg in self.args:
            out.append(repr(arg))
            out.append(", ")
        for name, value in self.kwargs.items():
            out.append(f"{name}={value!r}")
            out.append(", ")
        if len(out) > 1:
            out[-1] = ")"
        else:
            out.append(")")
        return ''.join(out)

    def __antidote_debug_info__(self) -> DependencyDebug:
        return DependencyDebug(self.__antidote_debug_repr__(),
                               scope=self.scope,
                               dependencies=get_injections(self.func))

    def __antidote_provide__(self, container: Container) -> DependencyValue:
        return DependencyValue(self.func(*self.args, **self.kwargs), scope=self.scope)

    def __hash__(self) -> int:
        return object.__hash__(self)


@API.private
@final
class LazyProvider(StatelessProvider[Lazy]):
    def exists(self, dependency: Hashable) -> bool:
        return isinstance(dependency, Lazy)

    def debug(self, dependency: Lazy) -> DependencyDebug:
        return dependency.__antidote_debug_info__()

    def provide(self, dependency: Lazy, container: Container) -> DependencyValue:
        return dependency.__antidote_provide__(container)
