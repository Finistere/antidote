# @formatter:off
from typing import Hashable

cimport cython
from cpython.object cimport PyObject

from antidote.core.container cimport (Container, DependencyResult, DependencyValue, FastProvider)
from .._internal.utils import debug_repr
from ..core import DependencyDebug
from ..core.exceptions import DebugNotAvailableError

# @formatter:on

cdef extern from "Python.h":
    int PyObject_IsInstance(PyObject *inst, PyObject *cls) except -1


cdef class Lazy:
    def __antidote_debug_info__(self) -> DependencyDebug:
        raise DebugNotAvailableError()  # pragma: no cover

    cpdef __antidote_provide__(self, container: Container):
        raise NotImplementedError()  # pragma: no cover

    cdef fast_provide(self, PyObject*container, DependencyResult*result):
        cdef:
            DependencyValue dependency_instance
        dependency_instance = self.__antidote_provide__(<Container> container)
        if dependency_instance is not None:
            dependency_instance.to_result(result)

@cython.final
cdef class LazyProvider(FastProvider):
    cpdef LazyProvider clone(self, bint keep_singletons_cache):
        return LazyProvider.__new__(LazyProvider)

    def exists(self, dependency: Hashable) -> bool:
        return isinstance(dependency, Lazy)

    def maybe_debug(self, dependency: Hashable):
        if isinstance(dependency, Lazy):
            try:
                return dependency.__antidote_debug_info__()
            except DebugNotAvailableError:
                import warnings
                warnings.warn(f"Debug information for {debug_repr(dependency)} "
                              f"not available in {type(self)}")

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        if PyObject_IsInstance(dependency, <PyObject*> Lazy):
            return (<Lazy> dependency).fast_provide(container, result)
