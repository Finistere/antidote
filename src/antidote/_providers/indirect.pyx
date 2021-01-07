from typing import Callable, Dict, Hashable, Optional

# @formatter:off
cimport cython
from cpython.ref cimport PyObject, Py_XDECREF

from antidote.core.container cimport (DependencyResult, FastProvider, Header, header_strictest, header_flag_singleton, header_flag_no_scope,
                                      RawContainer, header_flag_cacheable)
from .._internal.utils import debug_repr
from ..core.exceptions import DependencyNotFoundError
from ..core import DependencyDebug, Scope

# @formatter:on

cdef extern from "Python.h":
    int PyDict_SetItem(PyObject *p, PyObject *key, PyObject *val) except -1
    PyObject*PyDict_GetItem(PyObject *p, PyObject *key)
    PyObject*PyObject_CallObject(PyObject *callable, PyObject *args) except NULL


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
                        scope=Scope.singleton(),
                        dependencies=[target])
                else:
                    return DependencyDebug(
                        f"Permanent link: {repr_d} -> ??? "
                        f"defined by {repr_linker}",
                        scope=Scope.singleton())
            else:
                return DependencyDebug(
                    f"Dynamic link: {repr_d} -> ??? defined by {repr_linker}",
                    scope=None,
                    wired=[link.linker])

        try:
            target = self.__static_links[dependency]
        except KeyError:
            pass
        else:
            repr_d = debug_repr(dependency)
            return DependencyDebug(f"Static link: {repr_d} -> {debug_repr(target)}",
                                   scope=Scope.singleton(),
                                   dependencies=[target])

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        cdef:
            PyObject* ptr
            PyObject* target

        ptr = PyDict_GetItem(<PyObject*> self.__static_links, dependency)
        if ptr:
            (<RawContainer> container).fast_get(ptr, result)
            result.header |= header_flag_cacheable()
            if result.value is NULL:
                raise DependencyNotFoundError(<object> ptr)
        else:
            ptr = PyDict_GetItem(<PyObject*> self.__links, dependency)
            if ptr:
                target = PyObject_CallObject(<PyObject*> (<Link> ptr).linker, NULL)
                (<RawContainer> container).fast_get(target, result)
                if result.value is NULL:
                    error = DependencyNotFoundError(<object> target)
                    Py_XDECREF(target)
                    raise error
                result.header = (header_strictest((<Link> ptr).header, result.header)
                                 | header_flag_cacheable())
                if (<Link> ptr).permanent:
                    PyDict_SetItem(<PyObject*> self.__static_links,
                                   dependency,
                                   target)
                Py_XDECREF(target)

    def register_static(self, dependency: Hashable, target_dependency: Hashable):
        with self._bound_container_ensure_not_frozen():
            self._bound_container_raise_if_exists(dependency)
            self.__static_links[dependency] = target_dependency

    def register_link(self, dependency: Hashable, linker: Callable[[], Hashable],
                      permanent: bool = True):
        with self._bound_container_ensure_not_frozen():
            self._bound_container_raise_if_exists(dependency)
            self.__links[dependency] = Link(linker, permanent)

@cython.final
cdef class Link:
    cdef:
        object linker
        bint permanent
        Header header

    def __init__(self, linker: Callable[[], Hashable], permanent: bool):
        self.linker = linker
        self.permanent = permanent
        self.header = header_flag_singleton() if permanent else header_flag_no_scope()
