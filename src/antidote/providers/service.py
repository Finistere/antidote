from __future__ import annotations

import inspect
from typing import Callable, Dict, Hashable, Optional, Union

from .._internal import API
from .._internal.utils import FinalImmutable, SlotRecord
from ..core import Dependency, DependencyContainer, DependencyInstance, DependencyProvider
from ..exceptions import DuplicateDependencyError


@API.private
class Build(FinalImmutable, copy=False):
    __slots__ = ('dependency', 'kwargs', '_hash')

    def __init__(self, dependency: Hashable, kwargs: Dict):
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

    def __eq__(self, other):
        return (isinstance(other, Build)
                and self._hash == other._hash
                and (self.dependency is other.dependency
                     or self.dependency == other.dependency)
                and self.kwargs == other.kwargs)  # noqa


@API.private
class ServiceProvider(DependencyProvider):
    def __init__(self):
        super().__init__()
        self.__services: Dict[Hashable, Service] = dict()

    def __repr__(self):
        return f"{type(self).__name__}(factories={tuple(self.__services.keys())!r})"

    def clone(self, keep_singletons_cache: bool) -> ServiceProvider:
        p = ServiceProvider()
        if keep_singletons_cache:
            p.__services = {
                k: s.copy() if s.factory_dependency is not None else s
                for k, s in self.__services.items()
            }
        else:
            p.__services = {
                k: s.copy(factory=None) if s.factory_dependency is not None else s
                for k, s in self.__services.items()
            }
        return p

    def provide(self, build: Hashable, container: DependencyContainer
                ) -> Optional[DependencyInstance]:
        dependency = build.dependency if isinstance(build, Build) else build
        try:
            service = self.__services[dependency]
        except KeyError:
            return None

        if service.factory is None:
            f = container.provide(service.factory_dependency)
            factory = f.instance
            if f.singleton:
                service.factory = f.instance
        else:
            factory = service.factory

        if isinstance(build, Build):
            if service.takes_dependency:
                instance = factory(dependency, **build.kwargs) \
                    if build.kwargs else factory(dependency)
            else:
                instance = factory(**build.kwargs) if build.kwargs else factory()
        else:
            instance = factory(dependency) if service.takes_dependency else factory()

        return DependencyInstance(instance,
                                  singleton=service.singleton)

    def register(self, service: type, *, singleton: bool = True):
        self.register_with_factory(service, factory=service,
                                   singleton=singleton, takes_dependency=False)
        return service

    def register_with_factory(self,
                              service: type,
                              *,
                              factory: Union[Callable, Dependency],
                              singleton: bool = True,
                              takes_dependency: bool = False):
        if not inspect.isclass(service):
            raise TypeError(f"service must be a class, not {service!r}")
        if not isinstance(singleton, bool):
            raise TypeError(f"singleton must be a boolean, not {singleton!r}")
        if not isinstance(takes_dependency, bool):
            raise TypeError(f"takes_dependency must be a boolean, "
                            f"not {takes_dependency!r}")

        if service in self.__services:
            raise DuplicateDependencyError(service,
                                           self.__services[service])
        if isinstance(factory, Dependency):
            self.__services[service] = Service(singleton=singleton,
                                               takes_dependency=takes_dependency,
                                               factory_dependency=factory.value)
        elif callable(factory):
            self.__services[service] = Service(singleton=singleton,
                                               takes_dependency=takes_dependency,
                                               factory=factory)
        else:
            raise TypeError(f"factory must be callable or a dependency, "
                            f"not {type(factory)!r}.")


@API.private
class Service(SlotRecord):
    __slots__ = ('singleton', 'takes_dependency', 'factory', 'factory_dependency')

    def __init__(self,
                 singleton: bool,
                 takes_dependency: bool,
                 factory: Callable = None,
                 factory_dependency: Hashable = None):
        assert factory is not None or factory_dependency is not None
        super().__init__(singleton, takes_dependency, factory, factory_dependency)
