from enum import Flag
from functools import reduce
from operator import __or__
from typing import Dict, Optional, Type

from ..core import DependencyInstance, DependencyProvider
from ..core.exceptions import DependencyNotFoundError


class ImplementationsPool:
    def __init__(self, profile_type: Type[Flag]):
        self.profile_type = profile_type
        self._profile_to_service = dict()  # type: Dict[Flag, type]

    def __setitem__(self, profile: Flag, service: type):
        if self._profile_to_service \
                and profile in reduce(__or__, self._profile_to_service.keys()):
            raise ValueError()
        self._profile_to_service[profile] = service

    def __getitem__(self, profile: Flag):
        return self._profile_to_service[profile]


class InterfaceProvider(DependencyProvider):
    def __init__(self, container):
        super(InterfaceProvider, self).__init__(container)
        self._multi_implementations = dict()  # type: Dict[type, ImplementationsPool]
        self._implementations = dict()  # type: Dict[type, type]

    def provide(self, dependency) -> Optional[DependencyInstance]:
        try:
            implementation = self._implementations[dependency]
        except KeyError:
            try:
                implementations = self._multi_implementations[dependency]
            except KeyError:
                return None
            else:
                profile_dependency = self._container.provide(
                    implementations.profile_type
                )
                if profile_dependency is None:
                    raise DependencyNotFoundError(implementations.profile_type)

                return DependencyInstance(
                    self._container.get(implementations[profile_dependency.instance]),
                    singleton=profile_dependency.singleton
                )
        else:
            return self._container.provide(implementation)

    def register(self, interface: type, implementation: type, profile: Flag = None):
        if not issubclass(implementation, interface):
            raise TypeError("implementation must be a subclass of interface.")

        if profile is None:
            if interface in self._multi_implementations \
                    or interface in self._implementations:
                raise ValueError()
            self._implementations[interface] = implementation
        elif isinstance(profile, Flag):
            if interface in self._implementations:
                raise ValueError()
            try:
                flag_to_impl = self._multi_implementations[interface]
            except KeyError:
                flag_to_impl = ImplementationsPool(type(profile))
                self._multi_implementations[interface] = flag_to_impl

            flag_to_impl[profile] = implementation
        else:
            raise TypeError("profile must be an instance of Flag")
