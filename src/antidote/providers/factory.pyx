from typing import Callable, Dict, Hashable, Union
from weakref import ref

# @formatter:off
cimport cython
from cpython.object cimport PyObject_Call, PyObject_CallObject
from cpython.ref cimport PyObject

from antidote.core.container cimport (DependencyResult, FastProvider, FLAG_DEFINED,
                                      FLAG_SINGLETON, PyObjectBox, RawContainer)
from antidote.providers.service cimport Build
from ..core import Dependency
from ..exceptions import DependencyNotFoundError, DuplicateDependencyError
# @formatter:on

cdef extern from "Python.h":
    int PyObject_IsInstance(PyObject *inst, PyObject *cls) except -1
    PyObject*PyDict_GetItem(PyObject *p, PyObject *key)


@cython.final
cdef class FactoryProvider(FastProvider):
    cdef:
        dict __factories
        tuple __empty_tuple
        object __weakref__

    def __init__(self):
        super().__init__()
        self.__factories: Dict[Hashable, Factory] = dict()
        self.__empty_tuple = tuple()

    def __repr__(self):
        return f"{type(self).__name__}(factories={self.__factories})"

    def clone(self, keep_singletons_cache: bool) -> FactoryProvider:
        cdef:
            Factory f
            FactoryProvider p

        p = FactoryProvider()
        if keep_singletons_cache:
            factories = {
                k: (f.copy() if f.dependency is not None else f)
                for k, f in self.__factories.items()
            }
        else:
            factories = {
                k: (f.copy_without_function() if f.dependency is not None else f)
                for k, f in self.__factories.items()
            }
        p.__factories = factories
        return p

    def has(self, dependency: Hashable) -> bool:
        dep = dependency.dependency if isinstance(dependency, Build) else dependency
        return isinstance(dep, FactoryDependency) and dep.dependency in self.__factories

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        cdef:
            PyObject*factory
            bint is_build_dependency = PyObject_IsInstance(dependency, <PyObject*> Build)
            PyObject*dependency_factory = (<PyObject*> (<Build> dependency).dependency
                                           if is_build_dependency else
                                           dependency)

        if not PyObject_IsInstance(dependency_factory, <PyObject*> FactoryDependency):
            return

        factory = PyDict_GetItem(<PyObject*> self.__factories,
                                 <PyObject*> (
                                     <FactoryDependency> dependency_factory).dependency)
        if factory == NULL:
            return

        if (<Factory> factory).function is None:
            (<RawContainer> container).fast_get(
                <PyObject*> (<Factory> factory).dependency, result)
            if result.flags == 0:
                raise DependencyNotFoundError((<Factory> factory).dependency)
            assert (
                               result.flags & FLAG_SINGLETON) != 0, "factory dependency is expected to be a singleton"
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
                 singleton: bool = True) -> FactoryDependency:
        with self._ensure_not_frozen():
            self._raise_if_exists_elsewhere(dependency)
            if dependency in self.__factories:
                raise DuplicateDependencyError(dependency,
                                               self.__factories[dependency])

            if isinstance(factory, Dependency):
                return self.__add(dependency,
                                  Factory(dependency=factory.value,
                                          singleton=singleton))
            elif callable(factory):
                return self.__add(dependency, Factory(singleton=singleton,
                                                      function=factory))
            else:
                raise TypeError(f"factory must be callable, not {type(factory)!r}.")

    def __add(self, dependency: Hashable, factory: Factory):
        self.__factories[dependency] = factory
        factory_dependency = FactoryDependency(dependency, ref(self))
        return factory_dependency

    def debug_get_registered_factory(self, dependency: Hashable
                                     ) -> Union[Callable, Dependency]:
        cdef:
            Factory factory = self.__factories[dependency]
        if factory.dependency is not None:
            return Dependency(factory.dependency)
        else:
            return factory.function

@cython.final
cdef class FactoryDependency:
    cdef:
        readonly object dependency
        object _provider_ref

    def __init__(self, object dependency, object provider_ref):
        self.dependency = dependency
        self._provider_ref = provider_ref

    def __repr__(self):
        provider = self._provider_ref()
        if provider is not None:
            factory = provider.debug_get_registered_factory(self.dependency)
            return f"FactoryDependency({self.dependency!r} @ {factory!r})"
        # Should not happen, but we'll try to provide some debug information
        return f"FactoryDependency({self.dependency!r} @ ???)"  # pragma: no cover

@cython.final
cdef class Factory:
    cdef:
        size_t flags
        object function
        object dependency

    def __init__(self,
                 bint singleton,
                 function: Callable = None,
                 dependency: Hashable = None):
        assert function is not None or dependency is not None
        self.flags = FLAG_SINGLETON if singleton else 0
        self.function = function
        self.dependency = dependency

    def __repr__(self):
        return (f"{type(self).__name__}(singleton={self.flags == FLAG_SINGLETON}, "
                f"function={self.function}, "
                f"dependency={self.dependency})")

    def copy(self):
        return Factory(self.flags == FLAG_SINGLETON,
                       self.function,
                       self.dependency)

    def copy_without_function(self):
        assert self.dependency is not None
        return Factory(self.flags == FLAG_SINGLETON,
                       None,
                       self.dependency)
