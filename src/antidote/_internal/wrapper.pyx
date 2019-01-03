# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False, annotation_typing=False

# @formatter:off
cimport cython
from cpython.dict cimport PyDict_Contains, PyDict_Copy, PyDict_SetItem

from antidote.core.container cimport DependencyContainer
from ..exceptions import DependencyNotFoundError
# @formatter:on

@cython.freelist(10)
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
        public object __wrapped__
        public str __module__
        public str __name__
        public str __qualname__
        public str __doc__
        public dict __annotations__
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
        return self.__wrapped__(*args, **kwargs)

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
    def __func__(self):
        return self.__wrapped__.__func__

    @property
    def __self__(self):
        return self.__wrapped__.__self__

cdef class InjectedBoundWrapper(InjectedWrapper):
    def __get__(self, instance, owner):
        return self

cdef dict _inject_kwargs(DependencyContainer container,
                         InjectionBlueprint blueprint,
                         int offset,
                         dict kwargs):
    cdef:
        Injection injection
        object instance
        bint dirty_kwargs = False
        int i

    for i in range(offset, len(blueprint.injections)):
        injection = blueprint.injections[i]
        if injection.dependency is not None \
                and PyDict_Contains(kwargs, injection.arg_name) == 0:
            instance = container.provide(injection.dependency)
            if instance is not container.SENTINEL:
                if not dirty_kwargs:
                    kwargs = PyDict_Copy(kwargs)
                    dirty_kwargs = True
                PyDict_SetItem(kwargs, injection.arg_name, <object> instance)
            elif injection.required:
                raise DependencyNotFoundError(injection.dependency)

    return kwargs
