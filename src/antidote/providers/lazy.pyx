# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False
from typing import Callable, Dict, Tuple, Union

# @formatter:off
from cpython.object cimport PyObject, PyObject_Call, PyObject_GetAttr
from antidote.core.container cimport (DependencyInstance, FastDependencyProvider,
                                      DependencyContainer, DependencyResult, PyObjectBox,
                                      FLAG_SINGLETON, FLAG_DEFINED)

# @formatter:on
from ..core.exceptions import DependencyNotFoundError

cdef extern from "Python.h":
    int PyObject_IsInstance(PyObject *inst, PyObject *cls) except -1


cdef class LazyCall:
    """
    Dependency which is the result of the call of the given function with the
    given arguments.

    .. doctest::

        >>> from antidote import LazyCall, world
        >>> def f(x, y):
        ...     print("Computing {} + {}".format(x, y))
        ...     return x + y
        >>> A = LazyCall(f)(2, y=3)
        >>> world.get(A)
        Computing 2 + 3
        5
    """
    cdef:
        object _func
        tuple _args
        dict _kwargs
        int _flags

    def __init__(self, func: Callable, singleton: bool = True):
        """
        Args:
            func: Function to lazily call, any arguments given by calling
                to the instance of :py:class:`~.LazyCall` will be passed on.
            singleton: Whether or not this is a singleton or not.
        """
        self._flags = FLAG_SINGLETON if singleton else 0
        self._func = func
        self._args = ()  # type: Tuple
        self._kwargs = {}  # type: Dict

    def __call__(self, *args, **kwargs):
        """
        All argument are passed on to the lazily called function.
        """
        self._args = args
        self._kwargs = kwargs
        return self

cdef class LazyMethodCall:
    """
    Similar to :py:class:`~.LazyCall` but adapted to methods within a class
    definition. The class has to be a registered service, as the class
    instantiation itself is also lazy.

    .. doctest::

        >>> from antidote import LazyMethodCall, register, world
        >>> @register
        ... class Constants:
        ...     def get(self, x: str):
        ...         return len(x)
        ...     A = LazyMethodCall(get)('test')
        >>> Constants.A
        LazyMethodCallDependency(...)
        >>> world.get(Constants.A)
        4
        >>> Constants().A
        4

    :py:class:`~.LazyMethodCall` has two different behaviors:

    - if retrieved as a class attribute it returns a dependency which identifies
      the result for Antidote.
    - if retrieved as a instance attribute it returns the result for this
      instance. This makes testing a lot easier as it does not require Antidote.

    Check out :py:class:`~.helpers.conf.LazyConstantsMeta` for simple way
    to declare multiple constants.
    """
    cdef:
        str _method_name
        int _flags
        tuple _args
        dict _kwargs
        str _key

    def __init__(self, method: Union[Callable, str], singleton: bool = True):
        self._flags = FLAG_SINGLETON if singleton else 0
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
            if self._flags == FLAG_SINGLETON:
                if self._key is None:
                    self._key = f"{self._get_attribute_name(owner)}_dependency"
                    setattr(owner,
                            self._key,
                            LazyMethodCallDependency.__new__(LazyMethodCallDependency,
                                                             self,
                                                             owner))
                return getattr(owner, self._key)
            return LazyMethodCallDependency.__new__(LazyMethodCallDependency, self, owner)
        return self._call(instance)

    cdef object _call(self, object instance):
        cdef:
            object method

        method = PyObject_GetAttr(instance, self._method_name)
        if <PyObject*> method == NULL:
            raise RuntimeError(f"{instance} does not have a method {self._method_name}")

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

cdef class LazyCallProvider(FastDependencyProvider):
    def clone(self) -> FastDependencyProvider:
        return self

    def freeze(self):
        pass

    cdef fast_provide(self,
                      PyObject* dependency,
                      PyObject* container,
                      DependencyResult* result):
        cdef:
            LazyMethodCall lazy_method_call
            DependencyInstance dependency_instance

        if PyObject_IsInstance(dependency, <PyObject*> LazyMethodCallDependency):
            (<DependencyContainer> container).fast_get(
                <PyObject*> (<LazyMethodCallDependency> dependency).owner,
                result
            )
            if result.flags == 0:
                raise DependencyNotFoundError(<object> dependency)
            lazy_method_call = (<LazyMethodCallDependency> dependency).lazy_method_call
            result.flags = FLAG_DEFINED | lazy_method_call._flags
            (<PyObjectBox> result.box).obj = lazy_method_call._call((<PyObjectBox> result.box).obj)

        elif PyObject_IsInstance(dependency, <PyObject*> LazyCall):
            result.flags = FLAG_DEFINED | (<LazyCall> dependency)._flags
            (<PyObjectBox> result.box).obj = PyObject_Call(
                (<LazyCall> dependency)._func,
                (<LazyCall> dependency)._args,
                (<LazyCall> dependency)._kwargs
            )
