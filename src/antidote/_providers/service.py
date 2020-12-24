import inspect
from typing import cast, Dict, Hashable, Optional

from .._internal import API
from .._internal.utils import debug_repr, FinalImmutable
from ..core import Container, DependencyInstance, Provider
from ..core.utils import DependencyDebug


@API.private
class Build(FinalImmutable):
    __slots__ = ('dependency', 'kwargs', '_hash')
    dependency: Hashable
    kwargs: dict
    _hash: int

    def __init__(self, dependency: Hashable, kwargs: dict):
        assert isinstance(kwargs, dict) and len(kwargs) > 0

        try:
            # Try most precise hash first
            _hash = hash((dependency, tuple(kwargs.items())))
        except TypeError:
            # If type error, return the best error-free hash possible
            _hash = hash((dependency, tuple(kwargs.keys())))

        super().__init__(dependency, kwargs, _hash)

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return f"Build(dependency={self.dependency}, kwargs={self.kwargs})"

    def __antidote_debug_repr__(self):
        return f"{debug_repr(self.dependency)}(**{self.kwargs})"

    def __eq__(self, other):
        return (isinstance(other, Build)
                and self._hash == other._hash
                and (self.dependency is other.dependency
                     or self.dependency == other.dependency)
                and self.kwargs == other.kwargs)  # noqa


@API.private
class ServiceProvider(Provider):
    def __init__(self):
        super().__init__()
        self.__services: Dict[Hashable, bool] = dict()

    def __repr__(self):
        return f"{type(self).__name__}(services={list(self.__services.items())!r})"

    def exists(self, dependency: Hashable) -> bool:
        if isinstance(dependency, Build):
            return dependency.dependency in self.__services
        return dependency in self.__services

    def clone(self, keep_singletons_cache: bool) -> 'ServiceProvider':
        p = ServiceProvider()
        p.__services = self.__services.copy()
        return p

    def maybe_debug(self, build: Hashable) -> Optional[DependencyDebug]:
        klass = build.dependency if isinstance(build, Build) else build
        try:
            singleton = self.__services[klass]
        except KeyError:
            return None
        return DependencyDebug(debug_repr(build),
                               singleton=singleton,
                               wired=[klass])

    def maybe_provide(self, build: Hashable, container: Container
                      ) -> Optional[DependencyInstance]:
        dependency = build.dependency if isinstance(build, Build) else build
        try:
            singleton = self.__services[dependency]
        except KeyError:
            return None

        klass = cast(type, dependency)
        if isinstance(build, Build) and build.kwargs:
            instance = klass(**build.kwargs)
        else:
            instance = klass()

        return DependencyInstance(instance, singleton=singleton)

    def register(self, klass: type, *, singleton: bool = True):
        if not (isinstance(klass, type) and inspect.isclass(klass)):
            raise TypeError(f"service must be a class, not {klass!r}")
        if not isinstance(singleton, bool):
            raise TypeError(f"singleton must be a boolean, not {singleton!r}")
        self._assert_not_duplicate(klass)
        self.__services[klass] = singleton
