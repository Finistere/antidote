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
        self.__factories: Dict[FactoryDependency, Factory] = dict()
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
                and dependency in self.__factories)

    def maybe_debug(self, build: Hashable) -> Optional[DependencyDebug]:
        cdef:
            Factory factory

        dependency_factory = build.dependency if isinstance(build, Build) else build
        if not isinstance(dependency_factory, FactoryDependency):
            return None

        try:
            factory = self.__factories[dependency_factory]
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
            PyObject*dependency_factory = (<PyObject*> (<Build> dependency).dependency
                                           if is_build_dependency else
                                           dependency)

        if not PyObject_IsInstance(dependency_factory, <PyObject*> FactoryDependency):
            return

        factory = PyDict_GetItem(<PyObject*> self.__factories, dependency_factory)
        if factory == NULL:
            return

        if (<Factory> factory).function is None:
            (<RawContainer> container).fast_get(<PyObject*> (<Factory> factory).dependency,
                                                result)
            if result.flags == 0:
                raise DependencyNotFoundError((<Factory> factory).dependency)
            assert (result.flags & FLAG_SINGLETON) == FLAG_SINGLETON, "factory dependency is expected to be a singleton"
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
                 output: Hashable,
                 factory: Union[Callable, Dependency],
                 singleton: bool = True) -> FactoryDependency:
        with self._bound_container_ensure_not_frozen():
            factory_dependency = FactoryDependency(output, factory)
            self._bound_container_raise_if_exists(factory_dependency)

            if isinstance(factory, Dependency):
                self.__factories[factory_dependency] = Factory(singleton,
                                                               dependency=factory.value)
            elif callable(factory):
                self.__factories[factory_dependency] = Factory(singleton,
                                                               function=factory)
            else:
                raise TypeError(f"factory must be callable, not {type(factory)!r}.")

            return factory_dependency

@cython.final
cdef class FactoryDependency:
    cdef:
        readonly object output
        readonly object factory
        int _hash

    def __init__(self, object output, object factory):
        self.output = output
        self.factory = factory
        self._hash = hash((output, factory))

    def __repr__(self) -> str:
        return f"FactoryDependency({self})"

    def __antidote_debug_repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"{debug_repr(self.output)} @ {debug_repr(self.factory)}"

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        cdef:
            FactoryDependency fd

        if not isinstance(other, FactoryDependency):
            return False

        fd = <FactoryDependency> other
        return (self._hash == fd._hash
                and (self.output is fd.output
                     or self.output == fd.output)
                and (self.factory is fd.factory
                     or self.factory == fd.factory))  # noqa

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
