# @formatter:off
from typing import Hashable, Callable, Tuple, Dict, Optional, Any

cimport cython
from cpython.object cimport PyObject
from antidote._internal.utils.debug import get_injections

from antidote.core.container cimport (Container, DependencyResult, DependencyValue, FastProvider,
                                      RawMarker, Scope, Header, HeaderObject)
from antidote._internal.utils import debug_repr
from antidote.core import DependencyDebug
from antidote.core.exceptions import DebugNotAvailableError

# @formatter:on

cdef extern from "Python.h":
    int PyObject_IsInstance(PyObject *inst, PyObject *cls) except -1
    PyObject *PyObject_Call(PyObject *callable, PyObject *args, PyObject *kwargs) except NULL
    PyObject *PyObject_CallObject(PyObject *callable, PyObject *args) except NULL


cdef class Lazy(RawMarker):
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


class LazyFunction:
    @classmethod
    def of(cls,
           func: Callable[..., Any],
           args: Tuple[Any, ...],
           kwargs: Dict[str, Any],
           scope: Optional[Scope]
           ) -> Lazy:
        cdef:
            Header header = HeaderObject.from_scope(scope).header
            LazyFunctionNoKwargs lazy_no_kwargs
            LazyFunctionWithKwargs lazy_with_kwargs

        if not kwargs:
            lazy_no_kwargs = LazyFunctionNoKwargs.__new__(LazyFunctionNoKwargs)
            lazy_no_kwargs.header = header
            lazy_no_kwargs.func = func
            lazy_no_kwargs.args = args
            lazy_no_kwargs.scope = scope
            return lazy_no_kwargs
        else:
            lazy_with_kwargs = LazyFunctionWithKwargs.__new__(LazyFunctionWithKwargs)
            lazy_with_kwargs.header = header
            lazy_with_kwargs.func = func
            lazy_with_kwargs.args = args
            lazy_with_kwargs.kwargs = kwargs
            lazy_with_kwargs.scope = scope
            return lazy_with_kwargs


cdef class LazyFunctionNoKwargs(Lazy):
    cdef:
        object func
        Scope scope
        Header header
        tuple args

    def __antidote_debug_repr__(self) -> str:
        return debug_func_repr(self.func, self.args, dict())

    def __antidote_debug_info__(self) -> DependencyDebug:
        return DependencyDebug(self.__antidote_debug_repr__(),
                               scope=self.scope,
                               dependencies=get_injections(self.func))

    cdef fast_provide(self, PyObject*container, DependencyResult*result):
        result.header = self.header
        result.value = PyObject_CallObject(
            <PyObject *> self.func,
            <PyObject *> self.args
        )


cdef class LazyFunctionWithKwargs(Lazy):
    cdef:
        object func
        Scope scope
        Header header
        tuple args
        dict kwargs

    def __antidote_debug_repr__(self) -> str:
        return debug_func_repr(self.func, self.args, self.kwargs)

    def __antidote_debug_info__(self) -> DependencyDebug:
        return DependencyDebug(self.__antidote_debug_repr__(),
                               scope=self.scope,
                               dependencies=get_injections(self.func))

    cdef fast_provide(self, PyObject*container, DependencyResult*result):
        result.header = self.header
        result.value = PyObject_Call(
            <PyObject *> self.func,
            <PyObject *> self.args,
            <PyObject *> self.kwargs
        )


cdef str debug_func_repr(object func, tuple args, dict kwargs):
    cdef:
        list out
    out = [f"{debug_repr(func)}("]
    for arg in args:
        out.append(repr(arg))
        out.append(", ")
    for name, value in kwargs.items():
        out.append(f"{name}={value!r}")
        out.append(", ")
    if len(out) > 1:
        out.pop()
    out.append(")")
    return ''.join(out)


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
