import inspect
from typing import Callable, Optional

# @formatter:off
cimport cython
from cpython.ref cimport PyObject

from antidote.core.container cimport (DependencyResult, FastProvider, header_flag_cacheable, RawContainer)
from .._internal.utils import debug_repr
from ..core import DependencyDebug, Scope
from ..core.exceptions import DependencyNotFoundError

# @formatter:on

cdef extern from "Python.h":
    PyObject *Py_None
    int PyDict_SetItem(PyObject *p, PyObject *key, PyObject *val) except -1
    PyObject *PyDict_GetItem(PyObject *p, PyObject *key)
    PyObject *PyObject_CallObject(PyObject *callable, PyObject *args) except NULL
    int PySet_Contains(PyObject *anyset, PyObject *key) except -1
    void Py_DECREF(PyObject *o)



@cython.final
cdef class IndirectProvider(FastProvider):
    cdef:
        dict __implementations

    def __cinit__(self, dict implementations = None):
        self.__implementations = implementations or dict()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(" \
               f"implementations={list(self.__implementations.keys())})"

    cpdef IndirectProvider clone(self, bint keep_singletons_cache):
        return IndirectProvider.__new__(IndirectProvider, self.__implementations.copy())

    def exists(self, dependency: object) -> bool:
        return (isinstance(dependency, ImplementationDependency)
                and dependency in self.__implementations)

    def maybe_debug(self, dependency: object) -> Optional[DependencyDebug]:
        cdef:
            ImplementationDependency impl

        if not isinstance(dependency, ImplementationDependency):
            return None

        try:
            target = self.__implementations[dependency]
        except KeyError:
            return None

        impl = <ImplementationDependency> dependency
        if target is None:
            target = impl.implementation()

        return DependencyDebug(debug_repr(impl),
                               scope=Scope.singleton() if impl.permanent else None,
                               wired=[impl.implementation],  # type: ignore
                               dependencies=[target])

    cdef fast_provide(self,
                      PyObject *dependency,
                      PyObject *container,
                      DependencyResult *result):
        cdef:
            PyObject *ptr
            PyObject *target

        ptr = PyDict_GetItem(<PyObject *> self.__implementations, dependency)
        if ptr is NULL:
            return
        elif ptr is not Py_None:
            (<RawContainer> container).fast_get(ptr, result)
            result.header |= header_flag_cacheable()
            if result.value is NULL:
                raise DependencyNotFoundError(<object> ptr)
        else:
            target = PyObject_CallObject(
                <PyObject *> (<ImplementationDependency> dependency).implementation,
                NULL
            )
            (<RawContainer> container).fast_get(target, result)
            if result.value is NULL:
                error = DependencyNotFoundError(<object> target)
                Py_DECREF(target)
                raise error

            if (<ImplementationDependency> dependency).permanent:
                result.header |= header_flag_cacheable()
                PyDict_SetItem(<PyObject *> self.__implementations,
                               dependency,
                               target)
            else:
                result.header = 0

            Py_DECREF(target)

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
        with self._bound_container_ensure_not_frozen():
            self._bound_container_raise_if_exists(impl)
            self.__implementations[impl] = None
            return impl

@cython.final
cdef class ImplementationDependency:
    cdef:
        readonly object interface
        readonly object implementation
        readonly bint permanent
        int _hash

    def __init__(self,
                 interface: object,
                 implementation: Callable[[], object],
                 permanent: bool):
        self.interface = interface
        self.implementation = implementation
        self.permanent = permanent
        self._hash = hash((interface, implementation))

    def __repr__(self) -> str:
        return f"Implementation({self})"

    def __antidote_debug_repr__(self) -> str:
        if self.permanent:
            return f"Permanent implementation: {self}"
        else:
            return f"Implementation: {self}"

    def __str__(self) -> str:
        impl = self.implementation  # type: ignore
        return f"{debug_repr(self.interface)} @ {debug_repr(impl)}"

    # Custom hash & eq necessary to find duplicates
    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        cdef:
            ImplementationDependency imd

        if not isinstance(other, ImplementationDependency):
            return False

        imd = <ImplementationDependency> other
        return (self._hash == imd._hash
                and (self.interface is imd.interface
                     or self.interface == imd.interface)
                and (self.implementation is imd.implementation  # type: ignore
                     or self.implementation == imd.implementation)  # type: ignore
                )  # noqa
