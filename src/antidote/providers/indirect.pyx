from typing import Callable, Dict, Hashable

# @formatter:off
cimport cython
from cpython.object cimport PyObject

from antidote.core.container cimport (DependencyResult, FastProvider,
                                      FLAG_SINGLETON, RawContainer)
from ..exceptions import DuplicateDependencyError

# @formatter:on

cdef extern from "Python.h":
    int PyDict_SetItem(PyObject *p, PyObject *key, PyObject *val) except -1
    PyObject*PyDict_GetItem(PyObject *p, PyObject *key)
    int PyDict_DelItem(PyObject *p, PyObject *key) except -1
    PyObject*PyObject_CallObject(PyObject *callable_object, PyObject *args) except NULL


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

    def has(self, dependency):
        return dependency in self.__static_links or dependency in self.__links

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        cdef:
            PyObject*ptr
            PyObject*target

        ptr = PyDict_GetItem(<PyObject*> self.__static_links, dependency)
        if ptr != NULL:
            (<RawContainer> container).fast_get(ptr, result)
        else:
            ptr = PyDict_GetItem(<PyObject*> self.__links, dependency)
            if ptr != NULL:
                target = PyObject_CallObject(<PyObject*> (<Link> ptr).linker, NULL)
                (<RawContainer> container).fast_get(target, result)
                result.flags &= (<Link> ptr).singleton_flag
                if (<Link> ptr).permanent:
                    PyDict_SetItem(<PyObject*> self.__static_links,
                                   dependency,
                                   target)
                    PyDict_DelItem(<PyObject*> self.__links, dependency)

    def register_static(self, dependency: Hashable, target_dependency: Hashable):
        with self._ensure_not_frozen():
            self.__check_no_duplicate(dependency)
            self.__static_links[dependency] = target_dependency

    def register_link(self, dependency: Hashable, linker: Callable[[], Hashable],
                      permanent: bool = True):
        with self._ensure_not_frozen():
            self.__check_no_duplicate(dependency)
            self.__links[dependency] = Link(linker, permanent)

    cdef __check_no_duplicate(self, dependency):
        self._raise_if_exists_elsewhere(dependency)
        if dependency in self.__static_links:
            raise DuplicateDependencyError(dependency,
                                           self.__static_links[dependency])
        if dependency in self.__links:
            raise DuplicateDependencyError(dependency,
                                           self.__links[dependency])

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
