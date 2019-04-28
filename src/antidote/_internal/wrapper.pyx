# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False

# @formatter:off
cimport cython
from cpython.dict cimport PyDict_Contains, PyDict_Copy, PyDict_SetItem
from cpython.object cimport PyObject_Call
from cpython.tuple cimport PyTuple_GET_ITEM,  PyTuple_Size

from antidote.core.container cimport DependencyContainer, DependencyInstance
from ..exceptions import DependencyNotFoundError
# @formatter:on

compiled = True

@cython.freelist(128)
cdef class Injection:
    cdef:
        readonly str arg_name
        readonly bint required
        readonly object dependency

    def __repr__(self):
        return "{}(arg_name={!r}, required={!r}, dependency={!r})".format(
            type(self).__name__,
            self.arg_name,
            self.required,
            self.dependency
        )

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
        # public attributes as those are going to be overwritten by
        # functools.wraps()
        readonly object __wrapped__
        DependencyContainer __container
        InjectionBlueprint __blueprint
        int __injection_offset

    def __cinit__(self,
                  DependencyContainer container,
                  InjectionBlueprint blueprint,
                  object wrapped,
                  bint skip_first = False):
        self.__wrapped__ = wrapped
        self.__container = container
        self.__blueprint = blueprint
        self.__injection_offset = 1 if skip_first else 0

    def __call__(self, *args, **kwargs):
        kwargs = _inject_kwargs(
            self.__container,
            self.__blueprint,
            self.__injection_offset + len(args),
            kwargs
        )
        return PyObject_Call(self.__wrapped__, args, kwargs)

    def __get__(self, instance, owner):
        return InjectedBoundWrapper.__new__(
            InjectedBoundWrapper,
            self.__container,
            self.__blueprint,
            self.__wrapped__.__get__(instance, owner),
            isinstance(self.__wrapped__, classmethod)
            or (not isinstance(self.__wrapped__, staticmethod) and instance is not None)
        )

    @property
    def __name__(self):
        return self.__wrapped__.__name__

    @property
    def __qualname__(self):
        return self.__wrapped__.__qualname__

    @property
    def __doc__(self):
        return self.__wrapped__.__doc__

    @property
    def __annotations__(self):
        return self.__wrapped__.__annotations__

    @property
    def __module__(self):
        return self.__wrapped__.__module__

    @property
    def __func__(self):
        return self.__wrapped__.__func__

    @property
    def __self__(self):
        return self.__wrapped__.__self__

cdef class InjectedBoundWrapper(InjectedWrapper):
    def __get__(self, instance, owner):
        return self

cdef inline dict _inject_kwargs(DependencyContainer container,
                                InjectionBlueprint blueprint,
                                int offset,
                                dict kwargs):
    cdef:
        Injection injection
        DependencyInstance dependency_instance
        bint dirty_kwargs = False
        int i

    for i in range(offset, PyTuple_Size(blueprint.injections)):
        injection = <Injection> PyTuple_GET_ITEM(blueprint.injections, i)
        if injection.dependency is not None \
                and PyDict_Contains(kwargs, injection.arg_name) == 0:
            dependency_instance = container.provide(injection.dependency)
            if dependency_instance is not None:
                if not dirty_kwargs:
                    kwargs = PyDict_Copy(kwargs)
                    dirty_kwargs = True
                PyDict_SetItem(kwargs, injection.arg_name, dependency_instance.instance)
            elif injection.required:
                raise DependencyNotFoundError(injection.dependency)

    return kwargs
