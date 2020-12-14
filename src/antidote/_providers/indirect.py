from typing import Callable, Dict, Hashable, Optional

from .._internal import API
from .._internal.utils import debug_repr, FinalImmutable
from ..core import Container, DependencyInstance, Provider
from ..core.utils import DependencyDebug


@API.private
class IndirectProvider(Provider[Hashable]):
    def __init__(self) -> None:
        super().__init__()
        self.__links: Dict[Hashable, Link] = dict()
        self.__static_links: Dict[Hashable, Hashable] = dict()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(links={self.__links}, " \
               f"static_links={self.__static_links})"

    def clone(self, keep_singletons_cache: bool) -> 'IndirectProvider':
        p = IndirectProvider()
        p.__links = self.__links.copy()
        p.__static_links = self.__static_links.copy()
        return p

    def exists(self, dependency: Hashable) -> bool:
        return dependency in self.__static_links or dependency in self.__links

    def maybe_debug(self, dependency: Hashable) -> Optional[DependencyDebug]:
        try:
            link = self.__links[dependency]
        except KeyError:
            pass
        else:
            repr_d = debug_repr(dependency)
            linker = link.linker  # type: ignore  # Mypy treats linker as a method
            repr_linker = debug_repr(linker)
            if link.permanent:
                if dependency in self.__static_links:
                    target = self.__static_links[dependency]
                    return DependencyDebug(
                        f"Permanent link: {repr_d} -> {debug_repr(target)} "
                        f"defined by {repr_linker}",
                        singleton=True,
                        dependencies=[target])
                else:
                    return DependencyDebug(
                        f"Permanent link: {repr_d} -> ??? "
                        f"defined by {repr_linker}",
                        singleton=True)
            else:
                return DependencyDebug(
                    f"Dynamic link: {repr_d} -> ??? defined by {repr_linker}",
                    singleton=False,
                    wired=[linker])

        try:
            target = self.__static_links[dependency]
        except KeyError:
            pass
        else:
            repr_d = debug_repr(dependency)
            return DependencyDebug(f"Static link: {repr_d} -> {debug_repr(target)}",
                                   singleton=True,
                                   dependencies=[target])
        return None

    def maybe_provide(self, dependency: Hashable, container: Container
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
            target = link.linker()  # type: ignore  # Mypy treats linker as a method
            if link.permanent:
                self.__static_links[dependency] = target
            t = container.provide(target)
            return DependencyInstance(
                t.value,
                singleton=t.singleton and link.permanent
            )

        return None

    def register_static(self, dependency: Hashable, target_dependency: Hashable) -> None:
        self._assert_not_duplicate(dependency)
        self.__static_links[dependency] = target_dependency

    def register_link(self, dependency: Hashable, linker: Callable[[], Hashable],
                      permanent: bool = True) -> None:
        self._assert_not_duplicate(dependency)
        self.__links[dependency] = Link(linker, permanent)


@API.private
class Link(FinalImmutable):
    __slots__ = ('linker', 'permanent')
    linker: Callable[[], Hashable]
    permanent: bool
