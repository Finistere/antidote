from __future__ import annotations

from typing import Callable, Dict, Hashable, Optional

from .._internal import API
from .._internal.utils import FinalImmutable
from ..core import DependencyContainer, DependencyInstance, DependencyProvider
from ..exceptions import DuplicateDependencyError


@API.private
class IndirectProvider(DependencyProvider):
    def __init__(self):
        super().__init__()
        self.__links: Dict[Hashable, Link] = dict()
        self.__static_links: Dict[Hashable, Hashable] = dict()

    def __repr__(self):
        return f"{type(self).__name__}(links={self.__links}, " \
               f"static_links={self.__static_links})"

    def clone(self, keep_singletons_cache: bool) -> IndirectProvider:
        p = IndirectProvider()
        p.__links = self.__links.copy()
        p.__static_links = self.__static_links.copy()
        return p

    def provide(self, dependency: Hashable, container: DependencyContainer
                ) -> Optional[DependencyInstance]:
        try:
            target = self.__static_links[dependency]
        except KeyError:
            pass
        else:
            return container.provide(target)

        try:
            link = self.__links[dependency]
        except KeyError:
            pass
        else:
            target = link.linker()
            if link.permanent:
                self.__static_links[dependency] = target
            t = container.provide(target)
            return DependencyInstance(
                t.instance,
                singleton=t.singleton and link.permanent
            )

        return None

    def register_static(self, dependency: Hashable, target_dependency: Hashable):
        self.__check_no_duplicate(dependency)
        self.__static_links[dependency] = target_dependency

    def register_link(self, dependency: Hashable, linker: Callable[[], Hashable],
                      permanent: bool = True):
        self.__check_no_duplicate(dependency)
        self.__links[dependency] = Link(linker, permanent)

    def __check_no_duplicate(self, dependency):
        if dependency in self.__static_links:
            raise DuplicateDependencyError(dependency,
                                           self.__static_links[dependency])
        if dependency in self.__links:
            raise DuplicateDependencyError(dependency,
                                           self.__links[dependency])


@API.private
class Link(FinalImmutable):
    __slots__ = ('linker', 'permanent')
    linker: Callable[[], Hashable]
    permanent: bool
