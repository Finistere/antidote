# @formatter:off
from typing import Hashable
cimport cython
from cpython.object cimport PyObject, PyObject_CallMethodObjArgs

from antidote.core.container cimport (DependencyInstance, FastProvider, RawContainer,
                                      DependencyResult,  Container, PyObjectBox,
                                      FLAG_SINGLETON, FLAG_DEFINED)
from .._internal.utils import debug_repr
from ..core.utils import DependencyDebug
from ..exceptions import DependencyNotFoundError

# @formatter:on

cdef extern from "Python.h":
    int PyObject_IsInstance(PyObject *inst, PyObject *cls) except -1


cdef class Lazy:
    def debug_info(self) -> DependencyDebug:
        raise NotImplementedError()  # pragma: no cover

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
cdef class FastLazyConst(Lazy):
    cdef:
        object dependency
        str method_name
        object value

    def __init__(self, object dependency, str method_name, object value):
        self.dependency = dependency
        self.method_name = method_name
        self.value = value

    def debug_info(self) -> DependencyDebug:
        from ..helpers.lazy import LazyCall
        if isinstance(self.dependency, LazyCall):
            cls = self.dependency.func
        else:
            cls = self.dependency
        return DependencyDebug(f"Const calling {self.method_name} with {self.value!r} on "
                               f"{debug_repr(self.dependency)}",
                               singleton=True,
                               dependencies=[self.dependency],
                               wired=[getattr(cls, self.method_name)])

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

    def exists(self, dependency: Hashable) -> bool:
        return isinstance(dependency, Lazy)

    def maybe_debug(self, dependency: Hashable):
        if isinstance(dependency, Lazy):
            return dependency.debug_info()

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        if PyObject_IsInstance(dependency, <PyObject*> Lazy):
            return (<Lazy> dependency).fast_lazy_get(container, result)
