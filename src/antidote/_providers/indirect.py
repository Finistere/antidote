from __future__ import annotations

import inspect
from typing import Callable, Dict, Optional

from typing_extensions import Protocol

from .._internal import API
from .._internal.utils import debug_repr, FinalImmutable
from ..core import Container, DependencyDebug, DependencyValue, Provider, Scope


@API.private
class IndirectProvider(Provider[object]):
    def __init__(self) -> None:
        super().__init__()
        self.__implementations: Dict[ImplementationDependency, object] = dict()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(" \
               f"implementations={list(self.__implementations.keys())})"

    def clone(self, keep_singletons_cache: bool) -> IndirectProvider:
        p = IndirectProvider()
        p.__implementations = self.__implementations.copy()
        return p

    def exists(self, dependency: object) -> bool:
        return (isinstance(dependency, ImplementationDependency)
                and dependency in self.__implementations)

    def maybe_debug(self, dependency: object) -> Optional[DependencyDebug]:
        if not isinstance(dependency, ImplementationDependency):
            return None

        try:
            target = self.__implementations[dependency]
        except KeyError:
            return None

        if target is None:
            target = dependency.implementation()

        return DependencyDebug(debug_repr(dependency),
                               scope=Scope.singleton() if dependency.permanent else None,
                               wired=[dependency.implementation],
                               dependencies=[target])

    def maybe_provide(self, dependency: object, container: Container
                      ) -> Optional[DependencyValue]:
        if not isinstance(dependency, ImplementationDependency):
            return None

        try:
            target = self.__implementations[dependency]
        except KeyError:
            return None

        if target is not None:
            return container.provide(target)
        else:
            # Mypy treats linker as a method
            target = dependency.implementation()
            if dependency.permanent:
                self.__implementations[dependency] = target
            value = container.provide(target)
            return DependencyValue(
                value.unwrapped,
                scope=value.scope if dependency.permanent else None
            )

    def register_implementation(self,
                                interface: type,
                                implementation: Callable[[], object],
                                *,
                                permanent: bool
                                ) -> ImplementationDependency:
        assert callable(implementation) \
               and inspect.isclass(interface) \
               and isinstance(permanent, bool)
        impl = ImplementationDependency(interface, implementation, permanent)
        self._assert_not_duplicate(impl)
        self.__implementations[impl] = None
        return impl


class ImplementationCallback(Protocol):
    def __call__(self) -> object:
        ...


@API.private
class ImplementationDependency(FinalImmutable):
    __slots__ = ('interface', 'implementation', 'permanent', '__hash')
    interface: type
    implementation: ImplementationCallback
    permanent: bool
    __hash: int

    def __init__(self,
                 interface: object,
                 implementation: Callable[[], object],
                 permanent: bool):
        super().__init__(interface,
                         implementation,
                         permanent,
                         hash((interface, implementation)))

    def __repr__(self) -> str:
        return f"Implementation({self})"

    def __antidote_debug_repr__(self) -> str:
        if self.permanent:
            return f"Permanent implementation: {self}"
        else:
            return f"Implementation: {self}"

    def __str__(self) -> str:
        impl = self.implementation
        return f"{debug_repr(self.interface)} @ {debug_repr(impl)}"

    # Custom hash & eq necessary to find duplicates
    def __hash__(self) -> int:
        return self.__hash

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, ImplementationDependency)
                and self.__hash == other.__hash
                and (self.interface is other.interface
                     or self.interface == other.interface)
                and (self.implementation is other.implementation
                     or self.implementation == other.implementation)
                )  # noqa
