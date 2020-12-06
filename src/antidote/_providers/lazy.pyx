# @formatter:off
from typing import Hashable
cimport cython
from cpython.object cimport PyObject, PyObject_CallMethodObjArgs, PyObject_CallObject

from antidote.core.container cimport (Container, DependencyResult, FastProvider,
                                      FLAG_DEFINED, FLAG_SINGLETON, PyObjectBox,
                                      RawContainer, DependencyInstance)
from .._internal.utils import debug_repr
from ..core.exceptions import DependencyNotFoundError
from ..core.utils import DependencyDebug

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
        str name
        object dependency
        str method_name
        object value
        object cast

    def __init__(self, str name, object dependency, str method_name, object value,
                 object cast):
        self.name = name
        self.dependency = dependency
        self.method_name = method_name
        self.value = value
        self.cast = cast

    def debug_info(self) -> DependencyDebug:
        from ..lazy import LazyCall
        if isinstance(self.dependency, LazyCall):
            cls = self.dependency.func
        else:
            cls = self.dependency
        return DependencyDebug(f"Const: {debug_repr(cls)}.{self.name}",
                               singleton=True,
                               dependencies=[self.dependency],
                               wired=[getattr(cls, self.method_name)])

    cdef fast_lazy_get(self, PyObject*container, DependencyResult*result):
        (<RawContainer> container).fast_get(<PyObject*> self.dependency, result)
        if result.flags != 0:
            result.flags = FLAG_DEFINED | FLAG_SINGLETON
            (<PyObjectBox> result.box).obj = PyObject_CallObject(
                self.cast,
                (PyObject_CallMethodObjArgs((<PyObjectBox> result.box).obj,
                                           self.method_name,
                                           <PyObject*> self.value,
                                           NULL),)
            )
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
