import inspect
from typing import Dict, Hashable, Optional, Tuple, cast

from .._internal import API
from .._internal.utils import FinalImmutable, debug_repr
from ..core import Container, DependencyDebug, DependencyValue, Provider, Scope


@API.private
class Parameterized(FinalImmutable):
    __slots__ = ('wrapped', 'parameters', '_hash')
    wrapped: Hashable
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
class ServiceProvider(Provider[Hashable]):
    def __init__(self) -> None:
        super().__init__()
        self.__services: Dict[Hashable, Optional[Scope]] = dict()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(services={list(self.__services.items())!r})"

    def exists(self, dependency: Hashable) -> bool:
        if isinstance(dependency, Parameterized):
            return dependency.wrapped in self.__services
        return dependency in self.__services

    def clone(self, keep_singletons_cache: bool) -> 'ServiceProvider':
        p = ServiceProvider()
        p.__services = self.__services.copy()
        return p

    def maybe_debug(self, build: Hashable) -> Optional[DependencyDebug]:
        klass = build.wrapped if isinstance(build, Parameterized) else build
        try:
            scope = self.__services[klass]
        except KeyError:
            return None
        return DependencyDebug(debug_repr(build),
                               scope=scope,
                               wired=[klass])

    def maybe_provide(self, dependency: Hashable, container: Container
                      ) -> Optional[DependencyValue]:
        dep = dependency.wrapped if isinstance(dependency, Parameterized) else dependency
        try:
            scope = self.__services[dep]
        except KeyError:
            return None

        klass = cast(type, dep)
        if isinstance(dependency, Parameterized):
            instance = klass(**dependency.parameters)
        else:
            instance = klass()

        return DependencyValue(instance, scope=scope)

    def register(self,
                 klass: type,
                 *,
                 scope: Optional[Scope]
                 ) -> None:
        assert inspect.isclass(klass) \
               and (isinstance(scope, Scope) or scope is None)
        self._assert_not_duplicate(klass)
        self.__services[klass] = scope
