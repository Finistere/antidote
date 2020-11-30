import inspect
from typing import Dict, Hashable

# @formatter:off
cimport cython
from cpython.object cimport PyObject_Call, PyObject_CallObject
from cpython.ref cimport PyObject

from antidote.core.container cimport (DependencyResult, FastProvider,
                                      FLAG_DEFINED, FLAG_SINGLETON, PyObjectBox )
from .._internal.utils import debug_repr
# @formatter:on
from ..core.utils import DependencyDebug

cdef extern from "Python.h":
    int PyObject_IsInstance(PyObject *inst, PyObject *cls) except -1
    PyObject*PyDict_GetItem(PyObject *p, PyObject *key)
    PyObject*Py_True


@cython.final
cdef class Build:
    def __init__(self, dependency: Hashable, kwargs: Dict):
        assert isinstance(kwargs, dict) and len(kwargs) > 0
        self.dependency = dependency  # type: Hashable
        self.kwargs = kwargs  # type: Dict

        try:
            # Try most precise hash first
            self._hash = hash((self.dependency, tuple(self.kwargs.items())))
        except TypeError:
            # If type error, return the best error-free hash possible
            self._hash = hash((self.dependency, tuple(self.kwargs.keys())))

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return f"Build(dependency={self.dependency}, kwargs={self.kwargs})"

    def __antidote_debug_repr__(self):
        return f"{debug_repr(self.dependency)}(**{self.kwargs})"

    def __eq__(self, other):
        return (isinstance(other, Build)
                and self._hash == other._hash
                and (self.dependency is other.dependency
                     or self.dependency == other.dependency)
                and self.kwargs == other.kwargs)  # noqa

@cython.final
cdef class ServiceProvider(FastProvider):
    """
    Provider managing factories. Also used to register classes directly.
    """
    cdef:
        dict __services
        tuple __empty_tuple

    def __init__(self):
        super().__init__()
        self.__empty_tuple = tuple()
        self.__services = dict()  # type: Dict[Hashable, bool]

    def __repr__(self):
        return f"{type(self).__name__}(services={list(self.__services.items())!r})"

    def exists(self, dependency: Hashable) -> bool:
        if isinstance(dependency, Build):
            return dependency.dependency in self.__services
        return dependency in self.__services

    def clone(self, keep_singletons_cache: bool) -> ServiceProvider:
        p = ServiceProvider()
        p.__services = self.__services.copy()
        return p

    def maybe_debug(self, build: Hashable):
        klass = build.dependency if isinstance(build, Build) else build
        try:
            singleton = self.__services[klass]
        except KeyError:
            return None
        return DependencyDebug(debug_repr(build),
                               singleton=singleton,
                               wired=[klass])

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        cdef:
            PyObject*service
            PyObject*singleton
            tuple args
            object factory

        if PyObject_IsInstance(dependency, <PyObject*> Build):
            singleton = PyDict_GetItem(<PyObject*> self.__services,
                                       <PyObject*> (<Build> dependency).dependency)

            if singleton == NULL:
                return
            (<PyObjectBox> result.box).obj = PyObject_Call(
                (<Build> dependency).dependency,
                self.__empty_tuple,
                (<Build> dependency).kwargs
            )
        else:
            singleton = PyDict_GetItem(<PyObject*> self.__services, dependency)
            if singleton == NULL:
                return
            (<PyObjectBox> result.box).obj = PyObject_CallObject(<object> dependency,
                                                                 <object> NULL)

        result.flags = FLAG_DEFINED | (FLAG_SINGLETON if singleton == Py_True else 0)

    def register(self, klass: type, *, singleton: bool = True):
        if not (isinstance(klass, type) and inspect.isclass(klass)):
            raise TypeError(f"service must be a class, not {klass!r}")
        if not isinstance(singleton, bool):
            raise TypeError(f"singleton must be a boolean, not {singleton!r}")
        with self._ensure_not_frozen():
            self._raise_if_exists(klass)
            self.__services[klass] = singleton
