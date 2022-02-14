import inspect
from typing import Dict, Hashable

# @formatter:off
cimport cython
from cpython.ref cimport PyObject

from antidote.core.container cimport (DependencyResult, FastProvider, header_flag_cacheable, HeaderObject, Scope)
from .._internal.utils import debug_repr
# @formatter:on
from ..core import DependencyDebug

cdef extern from "Python.h":
    PyObject *Py_True
    int PyObject_IsInstance(PyObject *inst, PyObject *cls) except -1
    PyObject *PyDict_GetItem(PyObject *p, PyObject *key)
    PyObject *PyObject_Call(PyObject *callable, PyObject *args, PyObject *kwargs) except NULL
    PyObject *PyObject_CallObject(PyObject *callable, PyObject *args) except NULL

cdef:
    tuple empty_tuple = tuple()


@cython.final
cdef class Parameterized:
    def __init__(self, wrapped: Hashable, parameters: dict):
        assert isinstance(parameters, dict) and len(parameters) > 0
        self.wrapped = wrapped
        self.parameters = parameters

        try:
            self._hash = hash((self.wrapped, tuple(self.parameters.items())))
        except TypeError:
            self._hash = hash((self.wrapped, tuple(self.parameters.keys())))

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return f"Parameterized(dependency={self.wrapped}, parameters={self.parameters})"

    def __antidote_debug_repr__(self):
        return f"{debug_repr(self.wrapped)} with parameters={self.parameters}"

    def __eq__(self, other):
        return (isinstance(other, Parameterized)
                and self._hash == (<Parameterized> other)._hash
                and (self.wrapped is other.wrapped
                     or self.wrapped == other.wrapped)
                and self.parameters == other.parameters)  # noqa

@cython.final
cdef class ServiceProvider(FastProvider):
    """
    Provider managing factories. Also used to register classes directly.
    """
    cdef:
        dict __services

    def __cinit__(self, dict services = None):
        self.__services = services or dict()  # type: Dict[Hashable, HeaderObject]

    def __repr__(self):
        return f"{type(self).__name__}(services={list(self.__services.items())!r})"

    def exists(self, dependency: Hashable) -> bool:
        if isinstance(dependency, Parameterized):
            return dependency.wrapped in self.__services
        return dependency in self.__services

    cpdef ServiceProvider clone(self, bint keep_singletons_cache):
        return ServiceProvider.__new__(ServiceProvider, self.__services.copy())

    def maybe_debug(self, build: Hashable):
        klass = build.wrapped if isinstance(build, Parameterized) else build
        try:
            header = self.__services[klass]
        except KeyError:
            return None
        return DependencyDebug(debug_repr(build),
                               scope=header.to_scope(self._bound_container()),
                               wired=[klass])

    cdef fast_provide(self,
                      PyObject *dependency,
                      PyObject *container,
                      DependencyResult *result):
        cdef:
            PyObject *service
            PyObject *ptr
            tuple args
            object factory
            int scope_or_singleton

        if PyObject_IsInstance(dependency, <PyObject *> Parameterized):
            ptr = PyDict_GetItem(<PyObject *> self.__services,
                                 <PyObject *> (<Parameterized> dependency).wrapped)
            if ptr:
                result.header = (<HeaderObject> ptr).header
                result.value = PyObject_Call(
                    <PyObject *> (<Parameterized> dependency).wrapped,
                    <PyObject *> empty_tuple,
                    <PyObject *> (<Parameterized> dependency).parameters
                )
        else:
            ptr = PyDict_GetItem(<PyObject *> self.__services, dependency)
            if ptr:
                result.header = (<HeaderObject> ptr).header | header_flag_cacheable()
                result.value = PyObject_CallObject(dependency, NULL)

    def register(self, klass: type, *, Scope scope):
        assert inspect.isclass(klass) \
               and (isinstance(scope, Scope) or scope is None)
        with self._bound_container_ensure_not_frozen():
            self._bound_container_raise_if_exists(klass)
            self.__services[klass] = HeaderObject.from_scope(scope)
