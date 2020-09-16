import threading
from typing import Callable, Dict, Hashable, Optional

from .._internal.utils import API, SlotsReprMixin
from ..core import DependencyContainer, DependencyInstance, DependencyProvider
from ..exceptions import DuplicateDependencyError, FrozenWorldError


@API.private
class IndirectProvider(DependencyProvider):
    """
    IndirectProvider
    """

    def __init__(self):
        super(IndirectProvider, self).__init__()
        self.__links: Dict[Hashable, Link] = dict()
        self.__static_links: Dict[Hashable, Hashable] = dict()
        self.__freeze_lock = threading.RLock()
        self.__frozen = False

    def __repr__(self):
        return f"{type(self).__name__}(links={self.__links}, " \
               f"static_links={self.__static_links})"

    def freeze(self):
        with self.__freeze_lock:
            self.__frozen = True

    def clone(self) -> DependencyProvider:
        p = IndirectProvider()
        p.__static_links = self.__static_links.copy()
        p.__links = self.__links.copy()
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
            if link.static:
                self.__static_links[dependency] = target
                del self.__links[dependency]
            t = container.provide(target)
            return DependencyInstance(
                t.instance,
                singleton=t.singleton and link.static
            )

        return None

    def register_static(self, dependency: Hashable, target_dependency: Hashable,
                        override: bool = False):
        from antidote import world
        if not (world.is_test() and override):
            self.__check_no_duplicate(dependency)

        with self.__freeze_lock:
            if self.__frozen:
                raise FrozenWorldError(f"Cannot add {dependency} to a frozen world.")
            self.__static_links[dependency] = target_dependency

    def register_link(self, dependency: Hashable, linker: Callable[[], Hashable],
                      static: bool = True):
        self.__check_no_duplicate(dependency)

        with self.__freeze_lock:
            if self.__frozen:
                raise FrozenWorldError(f"Cannot add {dependency} to a frozen world.")
            self.__links[dependency] = Link(linker, static)

    def __check_no_duplicate(self, dependency):
        if dependency in self.__static_links:
            raise DuplicateDependencyError(dependency,
                                           self.__static_links[dependency])
        if dependency in self.__links:
            raise DuplicateDependencyError(dependency,
                                           self.__links[dependency])


@API.private
class Link(SlotsReprMixin):
    __slots__ = ('linker', 'static')

    def __init__(self, linker: Callable[[], Hashable], static: bool):
        self.linker = linker
        self.static = static
