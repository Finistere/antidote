from typing import Callable, Dict, Hashable, Union
from weakref import ref

# @formatter:off
cimport cython
from cpython.object cimport PyObject_Call, PyObject_CallObject
from cpython.ref cimport PyObject

from antidote.core.container cimport (RawDependencyContainer, FastDependencyProvider,
                                      DependencyResult, PyObjectBox, FLAG_DEFINED,
                                      FLAG_SINGLETON)
from antidote.providers.service cimport Build
from ..core import Dependency
from ..exceptions import DuplicateDependencyError, DependencyNotFoundError
# @formatter:on

cdef extern from "Python.h":
    int PyObject_IsInstance(PyObject *inst, PyObject *cls) except -1
    PyObject*PyDict_GetItem(PyObject *p, PyObject *key)


@cython.final
cdef class FactoryProvider(FastDependencyProvider):
    cdef:
        dict __dependencies
        tuple __empty_tuple

    def __init__(self):
        super().__init__()
        self.__dependencies = dict()  # type: Dict[Hashable, DependencyFactory]
        self.__empty_tuple = tuple()

    def __repr__(self):
        return f"{type(self).__name__}(factories={self.__dependencies.values()})"

    def clone(self) -> FactoryProvider:
        p = FactoryProvider()
        p.__dependencies = self.__dependencies.copy()
        return p

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        cdef:
            PyObject*factory
            bint is_build_dependency = PyObject_IsInstance(dependency, <PyObject*> Build)
            object dependency_factory


        if is_build_dependency:
            dependency_factory = (<Build> dependency).dependency
        else:
            dependency_factory = dependency

        if not PyObject_IsInstance(dependency_factory, <PyObject*> DependencyFactory):
            return

        factory = <PyObject*> (<DependencyFactory> dependency_factory).factory
        if (<Factory> factory).function_dependency is not None:
            (<RawDependencyContainer> container).fast_get(
                <PyObject*> (<Factory> factory).function_dependency, result)
            if result.flags == 0:
                raise DependencyNotFoundError((<Factory> factory).function_dependency)
            assert (result.flags & FLAG_SINGLETON) != 0, "factory dependency is expected to be a singleton"
            (<Factory> factory).function_dependency = None
            (<Factory> factory).function = (<PyObjectBox> result.box).obj

        result.flags = FLAG_DEFINED | (<Factory> factory).flags
        if is_build_dependency:
            (<PyObjectBox> result.box).obj = PyObject_Call(
                (<Factory> factory).function,
                self.__empty_tuple,
                (<Build> dependency).kwargs
            )
        else:
            (<PyObjectBox> result.box).obj = PyObject_CallObject(
                (<Factory> factory).function,
                <object> NULL
            )

    def register(self,
                 dependency: Hashable,
                 factory: Union[Callable, Dependency],
                 singleton: bool = True) -> DependencyFactory:
        # For now we don't support multiple factories for a single dependency.
        # Simply because I don't see a use case where it would make sense. In
        # Antidote the standard way would be to use `with_kwargs()` to customization
        # Open for discussions though, create an issue if you a use case.
        if dependency in self.__dependencies:
            raise DuplicateDependencyError(
                dependency,
                self.__dependencies[dependency]
            )
        if isinstance(factory, Dependency):
            return self.__add(dependency,
                              Factory(function_dependency=factory.value,
                                      singleton=singleton))
        elif callable(factory):
            return self.__add(dependency, Factory(singleton=singleton,
                                                  function=factory))
        else:
            raise TypeError(f"factory must be callable, not {type(factory)!r}.")

    def __add(self, dependency: Hashable, factory: Factory):
        dependency_factory = DependencyFactory(dependency, factory)
        self.__dependencies[dependency] = dependency_factory
        return dependency_factory

@cython.final
cdef class DependencyFactory:
    cdef:
        object dependency
        Factory factory

    def __init__(self, object dependency, Factory factory):
        self.dependency = dependency
        self.factory = factory

    def __repr__(self):
        return f"DependencyFactory({self.dependency!r} @ {self.factory!r})"

@cython.final
cdef class Factory:
    cdef:
        size_t flags
        object function
        object function_dependency

    def __init__(self,
                 bint singleton,
                 function: Callable = None,
                 function_dependency: Hashable = None):
        assert function is not None or function_dependency is not None
        assert function is None or function_dependency is None
        self.flags = FLAG_SINGLETON if singleton else 0
        self.function = function
        self.function_dependency = function_dependency

    def __repr__(self):
        return (f"{type(self).__name__}(singleton={self.flags == FLAG_SINGLETON}, "
                f"function={self.function}, "
                f"function_dependency={self.function_dependency})")

    def copy(self):
        return Factory(self.flags == FLAG_SINGLETON,
                       self.function,
                       self.function_dependency)
