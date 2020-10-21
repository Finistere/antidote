# @formatter:off
from typing import Hashable
cimport cython
from cpython.object cimport PyObject, PyObject_CallMethodObjArgs

from antidote.core.container cimport (DependencyInstance, FastProvider, RawContainer,
                                      DependencyResult,  Container, PyObjectBox,
                                      FLAG_SINGLETON, FLAG_DEFINED)
from ..exceptions import DependencyNotFoundError

# @formatter:on

cdef extern from "Python.h":
    int PyObject_IsInstance(PyObject *inst, PyObject *cls) except -1


cdef class Lazy:
    cdef fast_lazy_get(self, PyObject*container, DependencyResult*result):
        cdef:
            DependencyInstance dependency_instance

        dependency_instance = self.lazy_get(<Container> container)
        if dependency_instance is not None:
            result.flags = FLAG_DEFINED | (
                FLAG_SINGLETON if dependency_instance.singleton else 0)
            (<PyObjectBox> result.box).obj = dependency_instance.value

    cpdef lazy_get(self, container: Container):
        raise NotImplementedError()  # pragma: no cover


@cython.final
cdef class FastLazyMethod(Lazy):
    cdef:
        object dependency
        str method_name
        object value

    def __init__(self, object dependency, str method_name, object value):
        self.dependency = dependency
        self.method_name = method_name
        self.value = value

    cdef fast_lazy_get(self, PyObject*container, DependencyResult*result):
        (<RawContainer> container).fast_get(<PyObject*> self.dependency, result)
        if result.flags != 0:
            result.flags = FLAG_DEFINED | FLAG_SINGLETON
            (<PyObjectBox> result.box).obj = PyObject_CallMethodObjArgs(
                (<PyObjectBox> result.box).obj,
                self.method_name,
                <PyObject*> self.value,
                NULL)
        else:
            raise DependencyNotFoundError(self.dependency)


@cython.final
cdef class LazyProvider(FastProvider):
    def clone(self, keep_singletons_cache: bool) -> FastProvider:
        return LazyProvider()

    def has(self, dependency: Hashable) -> bool:
        return isinstance(dependency, Lazy)

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        if PyObject_IsInstance(dependency, <PyObject*> FastLazy):
            return (<FastLazy> dependency).fast_lazy_get(container, result)
