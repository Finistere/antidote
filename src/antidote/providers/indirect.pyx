from typing import Callable, Dict, Hashable, Optional

# @formatter:off
cimport cython
from cpython.object cimport PyObject, PyObject_CallObject

from antidote.core.container cimport (DependencyResult, FastProvider,
                                      FLAG_SINGLETON, RawContainer)
from .._internal.utils import debug_repr
from ..core.exceptions import DependencyNotFoundError
from ..core.utils import DependencyDebug

# @formatter:on

cdef extern from "Python.h":
    int PyDict_SetItem(PyObject *p, PyObject *key, PyObject *val) except -1
    PyObject*PyDict_GetItem(PyObject *p, PyObject *key)


@cython.final
cdef class IndirectProvider(FastProvider):
    cdef:
        dict __static_links
        dict __links

    def __init__(self):
        super().__init__()
        self.__links = dict()  # type: Dict[Hashable, Link]
        self.__static_links = dict()  # type: Dict[Hashable, Hashable]

    def __repr__(self):
        return f"{type(self).__name__}(links={self.__links}, " \
               f"static_links={self.__static_links})"

    def clone(self, keep_singletons_cache: bool) -> IndirectProvider:
        p = IndirectProvider()
        p.__links = self.__links.copy()
        p.__static_links = self.__static_links.copy()
        return p

    def exists(self, dependency) -> bool:
        return dependency in self.__static_links or dependency in self.__links

    def maybe_debug(self, dependency: Hashable) -> Optional[DependencyDebug]:
        cdef:
            Link link

        try:
            link = self.__links[dependency]
        except KeyError:
            pass
        else:
            repr_d = debug_repr(dependency)
            repr_linker = debug_repr(link.linker)
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
                    wired=[link.linker])

        try:
            target = self.__static_links[dependency]
        except KeyError:
            pass
        else:
            repr_d = debug_repr(dependency)
            return DependencyDebug(f"Static link: {repr_d} -> {debug_repr(target)}",
                                   singleton=True,
                                   dependencies=[target])

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        cdef:
            PyObject*ptr
            object target

        ptr = PyDict_GetItem(<PyObject*> self.__static_links, dependency)
        if ptr != NULL:
            (<RawContainer> container).fast_get(ptr, result)
            if result.flags == 0:
                raise DependencyNotFoundError(<object> ptr)
        else:
            ptr = PyDict_GetItem(<PyObject*> self.__links, dependency)
            if ptr != NULL:
                target = PyObject_CallObject((<Link> ptr).linker, <object> NULL)
                (<RawContainer> container).fast_get(<PyObject*> target, result)
                if result.flags == 0:
                    raise DependencyNotFoundError(target)
                result.flags &= (<Link> ptr).singleton_flag
                if (<Link> ptr).permanent:
                    PyDict_SetItem(<PyObject*> self.__static_links,
                                   dependency,
                                   <PyObject*> target)

    def register_static(self, dependency: Hashable, target_dependency: Hashable):
        with self._ensure_not_frozen():
            self._raise_if_exists(dependency)
            self.__static_links[dependency] = target_dependency

    def register_link(self, dependency: Hashable, linker: Callable[[], Hashable],
                      permanent: bool = True):
        with self._ensure_not_frozen():
            self._raise_if_exists(dependency)
            self.__links[dependency] = Link(linker, permanent)

@cython.final
cdef class Link:
    cdef:
        object linker
        bint permanent
        int singleton_flag

    def __init__(self, linker: Callable[[], Hashable], permanent: bool):
        self.linker = linker
        self.permanent = permanent
        self.singleton_flag = ~0 if permanent else ~FLAG_SINGLETON
