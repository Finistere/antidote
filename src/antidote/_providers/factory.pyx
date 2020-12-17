from typing import Callable, Dict, Hashable, Optional, Union
from weakref import ref

# @formatter:off
cimport cython
from cpython.object cimport PyObject_Call, PyObject_CallObject
from cpython.ref cimport PyObject

from antidote._providers.service cimport Build
from antidote.core.container cimport (DependencyResult, FastProvider, FLAG_DEFINED,
                                      FLAG_SINGLETON, PyObjectBox, RawContainer)
from .._internal.utils import debug_repr
from ..core import Dependency
from ..core.exceptions import DependencyNotFoundError
from ..core.utils import DependencyDebug
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

    def exists(self, dependency: Hashable) -> bool:
        if isinstance(dependency, Build):
            dependency = dependency.dependency
        return (isinstance(dependency, FactoryDependency)
                and dependency.dependency in self.__factories)

    def maybe_debug(self, build: Hashable) -> Optional[DependencyDebug]:
        cdef:
            Factory factory

        dependency_factory = build.dependency if isinstance(build, Build) else build
        if not isinstance(dependency_factory, FactoryDependency):
            return None

        try:
            factory = self.__factories[dependency_factory.dependency]
        except KeyError:
            return None

        return DependencyDebug(
            debug_repr(build),
            singleton=factory.singleton,
            wired=[factory.function] if factory.dependency is None else [],
            dependencies=([factory.dependency]
                          if factory.dependency is not None else []))

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        cdef:
            PyObject*factory
            bint is_build_dependency = PyObject_IsInstance(dependency, <PyObject*> Build)
            PyObject*dependency_factory = (<PyObject*> (<Build> dependency)._dependency
                                           if is_build_dependency else
                                           dependency)

        if not PyObject_IsInstance(dependency_factory, <PyObject*> FactoryDependency):
            return

        factory = PyDict_GetItem(<PyObject*> self.__factories,
                                 <PyObject*> (
                                     <FactoryDependency> dependency_factory)._dependency)
        if factory == NULL:
            return

        if (<Factory> factory).function is None:
            (<RawContainer> container).fast_get(
                <PyObject*> (<Factory> factory)._dependency, result)
            if result.flags == 0:
                raise DependencyNotFoundError((<Factory> factory)._dependency)
            assert (result.flags & FLAG_SINGLETON) != 0, "factory dependency is expected to be a singleton"
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
            factory_dependency = FactoryDependency(dependency, ref(self))
            self._raise_if_exists(factory_dependency)

            if isinstance(factory, Dependency):
                self.__factories[dependency] = Factory(singleton,
                                                       dependency=factory.value)
            elif callable(factory):
                self.__factories[dependency] = Factory(singleton, function=factory)
            else:
                raise TypeError(f"factory must be callable, not {type(factory)!r}.")

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
        return f"FactoryDependency({self})"

    def __antidote_debug_repr__(self):
        return str(self)

    def __str__(self):
        provider = self._provider_ref()
        dependency = debug_repr(self.dependency)
        if provider is not None:
            factory = provider.debug_get_registered_factory(self.dependency)
            return f"{dependency} @ {debug_repr(factory)}"
        # Should not happen, but we'll try to provide some debug information
        return f"{dependency} @ ???"  # pragma: no cover

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
        return (f"{type(self).__name__}(singleton={self.singleton}, "
                f"function={self.function}, "
                f"dependency={self.dependency})")

    @property
    def singleton(self):
        return self.flags == FLAG_SINGLETON

    def copy(self):
        return Factory(self.singleton,
                       self.function,
                       self.dependency)

    def copy_without_function(self):
        assert self.dependency is not None
        return Factory(self.singleton,
                       None,
                       self.dependency)
