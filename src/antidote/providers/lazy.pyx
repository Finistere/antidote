# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
from typing import Callable, Dict, Tuple, Union

# @formatter:off
from cpython.object cimport PyObject, PyObject_Call, PyObject_GetAttr

from antidote.core.container cimport DependencyInstance, DependencyProvider
from ..exceptions import  DependencyNotFoundError
# @formatter:on


cdef class LazyCall:
    def __init__(self, func: Callable, singleton = True):
        self._singleton = singleton
        self._func = func
        self._args = ()  # type: Tuple
        self._kwargs = {}  # type: Dict

    def __call__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        return self

cdef class LazyMethodCall:
    def __init__(self, method: Union[Callable, str], singleton: bool = True):
        self._singleton = singleton
        # Retrieve the name of the method, as injection can be done after the class
        # creation which is typically the case with @register.
        self._method_name = method if isinstance(method, str) else method.__name__
        self._args = ()  # type: Tuple
        self._kwargs = {}  # type: Dict
        self._key = None

    def __call__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        return self

    def __get__(self, instance, owner):
        if instance is None:
            if self._singleton:
                if self._key is None:
                    self._key = "{}_dependency".format(self._get_attribute_name(owner))
                    setattr(owner, self._key, LazyMethodCallDependency(self, owner))
                return getattr(owner, self._key)
            return LazyMethodCallDependency(self, owner)
        return self._call(instance)

    cdef object _call(self, object instance):
        cdef:
            object method

        method = PyObject_GetAttr(
            instance,
            self._method_name
        )
        if <PyObject*> method == NULL:
            raise RuntimeError("{} does not have a method {}".format(
                instance,
                self._method_name
            ))

        return PyObject_Call(method, self._args, self._kwargs)

    def _get_attribute_name(self, owner):
        for k, v in owner.__dict__.items():
            if v is self:
                return k

cdef class LazyMethodCallDependency:
    cdef:
        LazyMethodCall lazy_method_call
        object owner

    def __cinit__(self, lazy_method_call, owner):
        self.lazy_method_call = lazy_method_call
        self.owner = owner

cdef class LazyCallProvider(DependencyProvider):
    bound_dependency_types = (LazyMethodCallDependency, LazyCall)

    cpdef DependencyInstance provide(self, object dependency):
        cdef:
            LazyCall lazy_call
            LazyMethodCallDependency lazy_method_dependency
            object dependency_instance
            object method

        if isinstance(dependency, LazyMethodCallDependency):
            lazy_method_dependency = <LazyMethodCallDependency> dependency
            dependency_instance = self._container.provide(lazy_method_dependency.owner)
            if dependency_instance is None:
                raise DependencyNotFoundError(dependency_instance)

            return DependencyInstance.__new__(
                DependencyInstance,
                lazy_method_dependency.lazy_method_call._call(dependency_instance),
                lazy_method_dependency.lazy_method_call._singleton
            )
        elif isinstance(dependency, LazyCall):
            lazy_call = <LazyCall> dependency
            return DependencyInstance.__new__(
                DependencyInstance,
                PyObject_Call(lazy_call._func, lazy_call._args, lazy_call._kwargs),
                lazy_call._singleton
            )
