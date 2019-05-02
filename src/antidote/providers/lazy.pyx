# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False
from typing import Callable, Dict, Tuple, Union

# @formatter:off
from cpython.object cimport PyObject, PyObject_Call, PyObject_GetAttr

from antidote.core.container cimport DependencyInstance, DependencyProvider
# @formatter:on


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
    def __init__(self, func: Callable, singleton: bool = True):
        """
        Args:
            func: Function to lazily call, any arguments given by calling
                to the instance of :py:class:`~.LazyCall` will be passed on.
            singleton: Whether or not this is a singleton or not.
        """
        self._singleton = singleton
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
            DependencyInstance dependency_instance

        if isinstance(dependency, LazyMethodCallDependency):
            lazy_method_dependency = <LazyMethodCallDependency> dependency
            return DependencyInstance.__new__(
                DependencyInstance,
                lazy_method_dependency.lazy_method_call._call(
                    self._container.get(lazy_method_dependency.owner)
                ),
                lazy_method_dependency.lazy_method_call._singleton
            )
        elif isinstance(dependency, LazyCall):
            lazy_call = <LazyCall> dependency
            return DependencyInstance.__new__(
                DependencyInstance,
                PyObject_Call(lazy_call._func, lazy_call._args, lazy_call._kwargs),
                lazy_call._singleton
            )
