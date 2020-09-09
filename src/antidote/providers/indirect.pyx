# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False
import threading
from typing import Hashable, Dict, Callable

# @formatter:off
from cpython.object cimport PyObject, PyObject_CallObject

from antidote.core.container cimport (DependencyContainer, FastDependencyProvider,
                                      DependencyResult, FLAG_SINGLETON)
from ..exceptions import DuplicateDependencyError, FrozenWorldError

# @formatter:on

cdef extern from "Python.h":
    int PyDict_SetItem(PyObject *p, PyObject *key, PyObject *val) except -1
    PyObject* PyDict_GetItem(PyObject *p, PyObject *key)
    int PyDict_DelItem(PyObject *p, PyObject *key) except -1


cdef class IndirectProvider(FastDependencyProvider):
    cdef:
        dict __static_links
        dict __links
        object __freeze_lock
        bint __frozen

    def __init__(self):
        self.__links = dict()  # type: Dict[Hashable, Link]
        self.__static_links = dict()  # type: Dict[Hashable, Hashable]
        self.__freeze_lock = threading.RLock()
        self.__frozen = False

    def __repr__(self):
        return f"{type(self).__name__}(links={self.__links}, " \
               f"static_links={self.__static_links})"

    def freeze(self):
        with self.__freeze_lock:
            self.__frozen = True

    def clone(self) -> FastDependencyProvider:
        p = IndirectProvider()
        p.__static_links = self.__static_links.copy()
        p.__links = self.__links.copy()
        return p

    cdef fast_provide(self,
                      PyObject* dependency,
                      PyObject* container,
                      DependencyResult*result):
        cdef:
            PyObject* ptr
            object target

        ptr = PyDict_GetItem(<PyObject*> self.__static_links, dependency)
        if ptr != NULL:
            (<DependencyContainer> container).fast_get(ptr, result)
        else:
            ptr = PyDict_GetItem(<PyObject*> self.__links, dependency)
            if ptr != NULL:
                target = PyObject_CallObject((<Link> ptr).linker, <object> NULL)
                (<DependencyContainer> container).fast_get(<PyObject*> target, result)
                result.flags &= (<Link> ptr).singleton_flag
                if (<Link> ptr).static:
                    PyDict_SetItem(<PyObject*> self.__static_links, dependency, <PyObject*> target)
                    PyDict_DelItem(<PyObject*> self.__links, dependency)

    def register_static(self, dependency: Hashable, target_dependency: Hashable):
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

cdef class Link:
    cdef:
        object linker
        bint static
        int singleton_flag

    def __init__(self, linker: Callable[[], Hashable], static: bool):
        self.linker = linker
        self.static = static
        self.singleton_flag = ~0 if static else ~FLAG_SINGLETON
