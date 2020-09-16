# @formatter:off
cimport cython
from cpython.object cimport PyObject, PyObject_CallMethodObjArgs
from cpython.weakref cimport PyWeakref_GET_OBJECT

from antidote.core.container cimport (DependencyInstance, FastDependencyProvider,
                                      RawDependencyContainer, DependencyResult,
                                      DependencyContainer,
                                      PyObjectBox, FLAG_SINGLETON, FLAG_DEFINED)
# @formatter:on

from ..exceptions import DependencyNotFoundError

cdef extern from "Python.h":
    int PyObject_IsInstance(PyObject *inst, PyObject *cls) except -1


cdef class FastLazy:
    cdef fast_lazy_get(self, PyObject*container, DependencyResult*result):
        raise NotImplementedError()

cdef class Lazy(FastLazy):
    cdef fast_lazy_get(self, PyObject*container, DependencyResult*result):
        cdef:
            DependencyInstance dependency_instance

        dependency_instance = self._lazy_get(<DependencyContainer> container)
        if dependency_instance is not None:
            result.flags = FLAG_DEFINED | (
                FLAG_SINGLETON if dependency_instance.singleton else 0)
            (<PyObjectBox> result.box).obj = dependency_instance.instance

    cpdef _lazy_get(self, container: DependencyContainer) -> DependencyInstance:
        raise NotImplementedError()  # pragma: no cover

@cython.final
class FastLazyMethod(FastLazy):
    cdef:
        object dependency
        str method_name
        object value

    def __init__(self, object dependency, str method_name, object value):
        self.dependency = dependency
        self.method_name = method_name
        self.value = value

    cdef fast_lazy_get(self, PyObject*container, DependencyResult*result):
        (<RawDependencyContainer> container).fast_get(<PyObject*> self.dependency, result)
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
cdef class LazyProvider(FastDependencyProvider):
    def clone(self) -> FastDependencyProvider:
        return LazyProvider()

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        if PyObject_IsInstance(dependency, <PyObject*> FastLazy):
            return (<FastLazy> dependency).fast_lazy_get(container, result)
