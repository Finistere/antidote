"""
Cython version of the wrapper, doing the same thing but faster.
"""
# @formatter:off
cimport cython
# @formatter:off
cimport cython
from cpython.dict cimport PyDict_Copy, PyDict_New
from cpython.object cimport PyObject_Call, PyObject_CallMethodObjArgs
from cpython.ref cimport PyObject

from antidote._internal.state cimport fast_get_container
from antidote.core.container cimport DependencyResult, PyObjectBox, RawContainer
from ..core.exceptions import DependencyNotFoundError

# @formatter:on

# @formatter:on

cdef extern from "Python.h":
    PyObject*PyTuple_GET_ITEM(PyObject *p, Py_ssize_t pos)
    Py_ssize_t PyTuple_GET_SIZE(PyObject *p)
    int PyDict_Contains(PyObject *p, PyObject *key) except -1
    int PyDict_SetItem(PyObject *p, PyObject *key, PyObject *val) except -1


compiled = True

cdef class Injection:
    cdef:
        readonly str arg_name
        readonly bint required
        readonly object dependency

    def __repr__(self):
        return f"{type(self).__name__}(arg_name={self.arg_name!r}, " \
               f"required={self.required!r}, dependency={self.dependency!r})"

    def __init__(self, str arg_name, bint required, object dependency):
        self.arg_name = arg_name
        self.required = required
        self.dependency = dependency

cdef class InjectionBlueprint:
    cdef:
        readonly tuple injections

    def __init__(self, tuple injections):
        self.injections = injections

def build_wrapper(InjectionBlueprint blueprint,
                  object wrapped,
                  bint skip_first = False):
    """
    Not relying on __init__ neither __cinit__ makes initialization faster which
    is especially important during __get__ as a InjectedBoundWrapper needs to
    be created *every* time.
    """
    cdef:
        InjectedWrapper wrapper = InjectedWrapper.__new__(InjectedWrapper)
    wrapper.__wrapped__ = wrapped
    wrapper.__blueprint = blueprint
    wrapper.__injection_offset = 1 if skip_first else 0
    wrapper.__is_classmethod = isinstance(wrapped, classmethod)
    wrapper.__is_staticmethod = isinstance(wrapped, staticmethod)
    return wrapper

@cython.freelist(128)
cdef class InjectedWrapper:
    cdef:
        dict __dict__
        readonly object __wrapped__
        InjectionBlueprint __blueprint
        int __injection_offset
        bint __is_classmethod
        bint __is_staticmethod

    def __call__(self, *args, **kwargs):
        cdef:
            RawContainer container = fast_get_container()
            DependencyResult result
            PyObjectBox box = PyObjectBox.__new__(PyObjectBox)
            PyObject*injection
            PyObject*arg_name
            PyObject*injections = <PyObject*> self.__blueprint.injections
            bint dirty_kwargs = False
            Py_ssize_t i
            Py_ssize_t offset = self.__injection_offset + PyTuple_GET_SIZE(
                <PyObject*> args)
            Py_ssize_t n = PyTuple_GET_SIZE(injections)
        result.box = <PyObject*> box

        if kwargs:
            for i in range(offset, n):
                injection = PyTuple_GET_ITEM(injections, i)
                if (<Injection> injection).dependency is not None:
                    arg_name = <PyObject*> (<Injection> injection).arg_name
                    if PyDict_Contains(<PyObject*> kwargs, arg_name) == 0:
                        container.fast_get(
                            <PyObject*> (<Injection> injection).dependency, &result)
                        if result.flags != 0:
                            if not dirty_kwargs:
                                kwargs = PyDict_Copy(kwargs)
                                dirty_kwargs = True
                            PyDict_SetItem(<PyObject*> kwargs,
                                           arg_name,
                                           <PyObject*> box.obj)
                        elif (<Injection> injection).required:
                            raise DependencyNotFoundError(
                                (<Injection> injection).dependency)
        else:
            for i in range(offset, n):
                injection = PyTuple_GET_ITEM(injections, i)
                if (<Injection> injection).dependency is not None:
                    container.fast_get(<PyObject*> (<Injection> injection).dependency,
                                       &result)
                    if result.flags != 0:
                        if not dirty_kwargs:
                            kwargs = PyDict_New()
                            dirty_kwargs = True
                        PyDict_SetItem(
                            <PyObject*> kwargs,
                            <PyObject*> (<Injection> injection).arg_name,
                            <PyObject*> box.obj
                        )
                    elif (<Injection> injection).required:
                        raise DependencyNotFoundError((<Injection> injection).dependency)

        return PyObject_Call(self.__wrapped__, args, kwargs)

    def __get__(self, instance, owner):
        cdef:
            InjectedBoundWrapper wrapper = InjectedBoundWrapper.__new__(
                InjectedBoundWrapper)
        wrapper.__wrapped__ = PyObject_CallMethodObjArgs(self.__wrapped__,
                                                         "__get__",
                                                         <PyObject*> instance,
                                                         <PyObject*> owner,
                                                         NULL)
        wrapper.__blueprint = self.__blueprint
        if self.__is_classmethod or (not self.__is_staticmethod and instance is not None):
            wrapper.__injection_offset = 1
        else:
            wrapper.__injection_offset = 0
        wrapper.__is_classmethod = False
        wrapper.__is_staticmethod = False

        return wrapper

    def __getattr__(self, name):
        return getattr(self.__wrapped__, name)

cdef class InjectedBoundWrapper(InjectedWrapper):
    def __get__(self, instance, owner):
        return self
