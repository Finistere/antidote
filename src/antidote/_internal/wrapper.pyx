"""
Cython version of the wrapper, doing the same thing but faster.
"""
# @formatter:off
import inspect

cimport cython
from cpython.object cimport PyObject_Call, PyObject_CallMethodObjArgs
from cpython.ref cimport PyObject

from antidote._internal.state cimport fast_get_container
from antidote.core.container cimport (DependencyResult, RawContainer)
from ..core.exceptions import DependencyNotFoundError

# @formatter:on

cdef extern from "Python.h":
    PyObject *PyTuple_GET_ITEM(PyObject *p, Py_ssize_t pos)
    Py_ssize_t PyTuple_GET_SIZE(PyObject *p)
    int PyDict_Contains(PyObject *p, PyObject *key) except -1
    int PyDict_SetItem(PyObject *p, PyObject *key, PyObject *val) except -1
    Py_ssize_t PyDict_Size(PyObject *p)
    PyObject *PyDict_Copy(PyObject *p)
    PyObject *PyDict_New() except NULL
    void Py_DECREF(PyObject *o)
    void Py_INCREF(PyObject *o)


compiled = True

cdef class Injection:
    cdef:
        str arg_name
        bint optional
        bint required
        object dependency

    def __repr__(self):
        return f"Injection(arg_name={self.arg_name!r}, " \
               f"required={self.required!r}, " \
               f"dependency={self.dependency!r}," \
               f" optional={self.optional!r})"

    def __init__(self, str arg_name, bint required, object dependency, bint optional):
        self.arg_name = arg_name
        self.required = required
        self.dependency = dependency
        self.optional = optional

cdef class InjectionBlueprint:
    cdef:
        tuple injections

    def __init__(self, tuple injections):
        self.injections = injections

    def is_empty(self):
        cdef:
            Injection injection
        for injection in self.injections:
            if injection.dependency is not None:
                return False
        return True

    def __repr__(self):
        return f"InjectionBlueprint({','.join(map(repr, self.injections))})"

def build_wrapper(InjectionBlueprint blueprint,
                  object wrapped,
                  bint skip_first = False):
    """
    Not relying on __init__ neither __cinit__ makes initialization faster which
    is especially important during __get__ as a InjectedBoundWrapper needs to
    be created *every* time.
    """
    cdef:
        InjectedWrapper wrapper
    if inspect.iscoroutinefunction(wrapped):
        wrapper = AsyncInjectedWrapper.__new__(AsyncInjectedWrapper)
    else:
        wrapper = SyncInjectedWrapper.__new__(SyncInjectedWrapper)
    wrapper.__wrapped__ = wrapped
    wrapper.__blueprint = blueprint
    wrapper.__injection_offset = 1 if skip_first else 0
    return wrapper

def get_wrapper_injections(wrapper):
    if not isinstance(wrapper, InjectedWrapper):
        raise TypeError(f"Argument must be an {InjectedWrapper}")

    return (<InjectedWrapper> wrapper).get_injections()

def is_wrapper(x):
    return isinstance(x, InjectedWrapper)

def get_wrapped(x):
    assert isinstance(x, InjectedWrapper)
    return x.__wrapped__

@cython.freelist(128)
cdef class InjectedWrapper:
    cdef:
        dict __dict__
        readonly object __wrapped__
        InjectionBlueprint __blueprint
        int __injection_offset
        object __weakref__

    cdef dict get_injections(self):
        cdef:
            Injection inj
        return {inj.arg_name: inj.dependency
                for inj in self.__blueprint.injections
                if inj.dependency is not None}

    @property
    def __class__(self):
        return self.__wrapped__.__class__

    def __getattr__(self, name):
        return getattr(self.__wrapped__, name)

# SYNC

cdef class SyncInjectedWrapper(InjectedWrapper):
    def __call__(self, *args, **kwargs):
        kwargs = <object> build_kwargs(<PyObject *> args,
                                       <PyObject *> kwargs,
                                       <PyObject *> self)
        Py_DECREF(<PyObject *> kwargs)
        return PyObject_Call(self.__wrapped__, args, kwargs)

    def __get__(self, instance, owner):
        cdef:
            SyncInjectedBoundWrapper bound_wrapper = \
                SyncInjectedBoundWrapper.__new__(SyncInjectedBoundWrapper)
        setup_bound_wrapper(<PyObject *> self,
                            <PyObject *> bound_wrapper,
                            <PyObject *> instance,
                            <PyObject *> owner)
        return bound_wrapper

cdef class SyncInjectedBoundWrapper(SyncInjectedWrapper):
    def __get__(self, instance, owner):
        return self

# ASYNC

cdef class AsyncInjectedWrapper(InjectedWrapper):
    async def __call__(self, *args, **kwargs):
        kwargs = <object> build_kwargs(<PyObject *> args,
                                       <PyObject *> kwargs,
                                       <PyObject *> self)
        Py_DECREF(<PyObject *> kwargs)
        return await PyObject_Call(self.__wrapped__, args, kwargs)

    def __get__(self, instance, owner):
        cdef:
            AsyncInjectedBoundWrapper bound_wrapper = \
                AsyncInjectedBoundWrapper.__new__(AsyncInjectedBoundWrapper)
        setup_bound_wrapper(<PyObject *> self,
                            <PyObject *> bound_wrapper,
                            <PyObject *> instance,
                            <PyObject *> owner)
        return bound_wrapper

cdef class AsyncInjectedBoundWrapper(AsyncInjectedWrapper):
    def __get__(self, instance, owner):
        return self

# Mixin

cdef inline setup_bound_wrapper(PyObject *wrapper,
                                PyObject *bound_wrapper,
                                PyObject *instance,
                                PyObject *owner):
    (<InjectedWrapper> bound_wrapper).__wrapped__ = \
        PyObject_CallMethodObjArgs((<InjectedWrapper> wrapper).__wrapped__,
                                   "__get__",
                                   instance,
                                   owner,
                                   NULL)
    (<InjectedWrapper> bound_wrapper).__blueprint = (<InjectedWrapper> wrapper).__blueprint
    if instance != <PyObject *> None:
        (<InjectedWrapper> bound_wrapper).__injection_offset = 1
    else:
        (<InjectedWrapper> bound_wrapper).__injection_offset = 0

cdef PyObject * build_kwargs(PyObject *args,
                             PyObject *original_kwargs,
                             PyObject *wrapper) except NULL:
    cdef:
        RawContainer container = fast_get_container()
        DependencyResult result
        PyObject *injection
        PyObject *arg_name
        PyObject *kwargs = original_kwargs
        PyObject *injections = <PyObject *> (<InjectedWrapper> wrapper).__blueprint.injections
        Py_ssize_t i
        Py_ssize_t offset = (<InjectedWrapper> wrapper).__injection_offset + PyTuple_GET_SIZE(args)
        Py_ssize_t n = PyTuple_GET_SIZE(injections)

    if PyDict_Size(kwargs):
        for i in range(offset, n):
            injection = PyTuple_GET_ITEM(injections, i)
            if (<Injection> injection).dependency is not None:
                arg_name = <PyObject *> (<Injection> injection).arg_name
                if not PyDict_Contains(<PyObject *> kwargs, arg_name):
                    container.fast_get(<PyObject *> (<Injection> injection).dependency,
                                       &result)
                    if result.value:
                        if kwargs == original_kwargs:
                            kwargs = PyDict_Copy(original_kwargs)
                        PyDict_SetItem(<PyObject *> kwargs,
                                       arg_name,
                                       result.value)
                        Py_DECREF(result.value)
                    elif (<Injection> injection).optional:
                        if kwargs == original_kwargs:
                            kwargs = PyDict_Copy(original_kwargs)
                        PyDict_SetItem(<PyObject *> kwargs,
                                       arg_name,
                                       <PyObject *> None)
                    elif (<Injection> injection).required:
                        raise DependencyNotFoundError((<Injection> injection).dependency)
    else:
        for i in range(offset, n):
            injection = PyTuple_GET_ITEM(injections, i)
            if (<Injection> injection).dependency is not None:
                container.fast_get(<PyObject *> (<Injection> injection).dependency,
                                   &result)
                if result.value:
                    if kwargs == original_kwargs:
                        kwargs = PyDict_New()
                    PyDict_SetItem(
                        <PyObject *> kwargs,
                        <PyObject *> (<Injection> injection).arg_name,
                        result.value
                    )
                    Py_DECREF(result.value)
                elif (<Injection> injection).optional:
                    if kwargs == original_kwargs:
                        kwargs = PyDict_New()
                    PyDict_SetItem(<PyObject *> kwargs,
                                   <PyObject *> (<Injection> injection).arg_name,
                                   <PyObject *> None)
                elif (<Injection> injection).required:
                    raise DependencyNotFoundError((<Injection> injection).dependency)

    return kwargs
