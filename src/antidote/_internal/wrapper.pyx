# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False

# @formatter:off
cimport cython
from cpython.dict cimport PyDict_Copy, PyDict_New
from cpython.object cimport PyObject_Call
from cpython.ref cimport PyObject

from antidote._internal.state cimport get_container
from antidote.core.container cimport DependencyContainer, DependencyResult, PyObjectBox
from ..core.exceptions import DependencyNotFoundError
# @formatter:on

cdef extern from "Python.h":
    PyObject* PyTuple_GetItem(PyObject *p, Py_ssize_t pos)
    Py_ssize_t PyTuple_GET_SIZE(PyObject *p)
    int PyDict_Contains(PyObject *p, PyObject *key) except -1
    int PyDict_SetItem(PyObject *p, PyObject *key, PyObject *val) except -1

compiled = True

@cython.freelist(128)
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

cdef class InjectedWrapper:
    cdef:
        readonly object __wrapped__
        InjectionBlueprint __blueprint
        int __injection_offset
        dict __dict
        bint __is_classmethod
        bint __is_staticmethod

    def __cinit__(self,
                  InjectionBlueprint blueprint,
                  object wrapped,
                  bint skip_first = False):
        self.__wrapped__ = wrapped
        self.__blueprint = blueprint
        self.__injection_offset = 1 if skip_first else 0
        # allocate a dictionary only if necessary, it's not that common
        # to add attributes to a function.
        self.__dict = None
        self.__is_classmethod = isinstance(wrapped, classmethod)
        self.__is_staticmethod = isinstance(wrapped, staticmethod)

    def __call__(self, *args, **kwargs):
        cdef:
            DependencyContainer container = get_container()
            DependencyResult result
            PyObject* injection_ptr
            PyObject* arg_name
            PyObjectBox box = PyObjectBox.__new__(PyObjectBox)
            PyObject* injections = <PyObject*> self.__blueprint.injections
            bint dirty_kwargs = False
            Py_ssize_t i
            Py_ssize_t offset = self.__injection_offset + PyTuple_GET_SIZE(<PyObject*> args)
            Py_ssize_t n = PyTuple_GET_SIZE(injections)
        result.box = <PyObject*> box

        if kwargs:
            for i in range(offset, n):
                injection_ptr = PyTuple_GetItem(injections, i)
                if (<Injection> injection_ptr).dependency is not None:
                    arg_name = <PyObject*>(<Injection> injection_ptr).arg_name
                    if PyDict_Contains(<PyObject*> kwargs, arg_name) == 0:
                        container.fast_get(<PyObject*> (<Injection> injection_ptr).dependency, &result)
                        if result.flags != 0:
                            if not dirty_kwargs:
                                kwargs = PyDict_Copy(kwargs)
                                dirty_kwargs = True
                            PyDict_SetItem(<PyObject*>kwargs, arg_name, <PyObject*> box.obj)
                        elif (<Injection> injection_ptr).required:
                            raise DependencyNotFoundError((<Injection> injection_ptr).dependency)
        else:
            for i in range(offset, n):
                injection_ptr = PyTuple_GetItem(injections, i)
                if (<Injection> injection_ptr).dependency is not None:
                    container.fast_get(<PyObject*> (<Injection> injection_ptr).dependency, &result)
                    if result.flags != 0:
                        if not dirty_kwargs:
                            kwargs = PyDict_New()
                            dirty_kwargs = True
                        PyDict_SetItem(
                            <PyObject*> kwargs,
                            <PyObject*> (<Injection> injection_ptr).arg_name,
                            <PyObject*> box.obj
                        )
                    elif (<Injection> injection_ptr).required:
                        raise DependencyNotFoundError((<Injection> injection_ptr).dependency)

        return PyObject_Call(self.__wrapped__, args, kwargs)

    def __get__(self, instance, owner):
        return InjectedBoundWrapper.__new__(
            InjectedBoundWrapper,
            self.__blueprint,
            self.__wrapped__.__get__(instance, owner),
            self.__is_classmethod or (not self.__is_staticmethod and instance is not None)
        )

    def __getattr__(self, name):
        if self.__dict is not None:
            try:
                return self.__dict[name]
            except KeyError:
                pass
        return getattr(self.__wrapped__, name)

    def __setattr__(self, name, value):
        if self.__dict is None:
            self.__dict = dict()
        self.__dict[name] = value

    def __delattr__(self, name):
        if self.__dict is not None:
            try:
                del self.__dict[name]
            except KeyError:
                raise AttributeError(name)

cdef class InjectedBoundWrapper(InjectedWrapper):
    def __get__(self, instance, owner):
        return self
