from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, Hashable, Optional, TypeVar, Union

from antidote._internal import API
from antidote._internal.utils import debug_repr, FinalImmutable
from antidote.core import Container, DependencyDebug, DependencyValue, Provider, Scope

C = TypeVar('C', bound=type)


@API.deprecated
@API.private
class Parameterized(FinalImmutable):
    __slots__ = ('wrapped', 'parameters', '_hash')
    wrapped: Any
    parameters: Dict[str, object]
    _hash: int

    def __init__(self, dependency: Hashable, parameters: Dict[str, object]) -> None:
        assert isinstance(parameters, dict) and parameters

        try:
            # Try most precise hash first
            _hash = hash((dependency, tuple(parameters.items())))
        except TypeError:
            # If type error, use the best error-free hash possible
            _hash = hash((dependency, tuple(parameters.keys())))

        super().__init__(dependency, parameters, _hash)

    def __hash__(self) -> int:
        return self._hash

    def __repr__(self) -> str:
        return f"Parameterized(dependency={self.wrapped}, parameters={self.parameters})"

    def __antidote_debug_repr__(self) -> str:
        return f"{debug_repr(self.wrapped)} with parameters={self.parameters}"

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, Parameterized)
                and self._hash == other._hash
                and (self.wrapped is other.wrapped
                     or self.wrapped == other.wrapped)
                and self.parameters == other.parameters)  # noqa


@API.private
class InjectableProvider(Provider[Union[Parameterized, type]]):
    def __init__(self) -> None:
        super().__init__()
        self.__services: dict[type, tuple[Optional[Scope], Callable[..., object]]] = dict()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(services={list(self.__services.items())!r})"

    def exists(self, dependency: object) -> bool:
        if isinstance(dependency, Parameterized):
            return isinstance(dependency.wrapped, type) and dependency.wrapped in self.__services
        return dependency in self.__services

    def clone(self, keep_singletons_cache: bool) -> InjectableProvider:
        p = InjectableProvider()
        p.__services = self.__services.copy()
        return p

    def debug(self, dependency: Union[Parameterized, type]) -> DependencyDebug:
        if isinstance(dependency, Parameterized):
            assert isinstance(dependency.wrapped, type)
            klass = dependency.wrapped
        else:
            klass = dependency
        scope, factory = self.__services[klass]
        return DependencyDebug(debug_repr(dependency),
                               scope=scope,
                               wired=[factory])

    def maybe_provide(self,
                      dependency: object,
                      container: Container
                      ) -> Optional[DependencyValue]:
        if isinstance(dependency, Parameterized):
            if not isinstance(dependency.wrapped, type):
                # Parameterized is deprecated anyway.
                return None  # pragma: no cover
            klass: type = dependency.wrapped
        elif isinstance(dependency, type):
            klass = dependency
        else:
            return None
        try:
            scope, factory = self.__services[klass]
        except KeyError:
            return None

        if isinstance(dependency, Parameterized):
            instance = factory(**dependency.parameters)
        else:
            instance = factory()

        return DependencyValue(instance, scope=scope)

    def register(self,
                 klass: C,
                 *,
                 scope: Optional[Scope],
                 factory: Optional[Callable[[], C]] = None
                 ) -> None:
        assert inspect.isclass(klass) \
               and (isinstance(scope, Scope) or scope is None)
        self._assert_not_duplicate(klass)
        self.__services[klass] = scope, factory or klass
