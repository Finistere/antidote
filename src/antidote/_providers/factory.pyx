import inspect
from typing import Callable, Dict, Hashable, Optional

# @formatter:off
cimport cython
from cpython.ref cimport PyObject

from antidote._providers.service cimport Parameterized
from antidote.core.container cimport (DependencyResult, FastProvider, Header, header_flag_cacheable, header_is_singleton, HeaderObject, RawContainer, Scope)
from .._internal.utils import debug_repr
from ..core import DependencyDebug
from ..core.exceptions import DependencyNotFoundError
# @formatter:on

ctypedef Py_ssize_t Py_hash_t

cdef extern from "Python.h":
    int PyObject_IsInstance(PyObject *inst, PyObject *cls) except -1
    int PyDict_SetItem(PyObject *p, PyObject *key, PyObject *val) except -1
    PyObject *PyDict_GetItem(PyObject *p, PyObject *key)
    PyObject *PyObject_Call(PyObject *callable, PyObject *args,
                            PyObject *kwargs) except NULL
    PyObject *PyObject_CallObject(PyObject *callable, PyObject *args) except NULL
    void Py_DECREF(PyObject *o)

cdef:
    tuple empty_tuple = tuple()


cdef class FactoryProvider(FastProvider):
    cdef:
        dict __factories

    def __cinit__(self, dict factories = None):
        self.__factories = factories or dict()  # type: Dict[FactoryDependency, Factory]

    def __repr__(self):
        return f"{type(self).__name__}(factories={self.__factories})"

    cpdef FactoryProvider clone(self, bint keep_singletons_cache):
        cdef:
            ClonedFactoryProvider provider
        provider = ClonedFactoryProvider.__new__(ClonedFactoryProvider,
                                                 self.__factories.copy())
        provider.__keep_singletons_cache = keep_singletons_cache
        return provider

    def exists(self, dependency: Hashable) -> bool:
        if isinstance(dependency, Parameterized):
            dependency = dependency.wrapped
        return (isinstance(dependency, FactoryDependency)
                and dependency in self.__factories)

    def maybe_debug(self, dependency: Hashable) -> Optional[DependencyDebug]:
        cdef:
            Factory factory

        dependency_factory = dependency.wrapped if isinstance(dependency,
                                                              Parameterized) else dependency
        if not isinstance(dependency_factory, FactoryDependency):
            return None

        try:
            factory = self.__factories[dependency_factory]
        except KeyError:
            return None

        dependencies = []
        wired = []
        if factory.dependency is not None:
            dependencies.append(factory.dependency)
            if isinstance(factory.dependency, type) \
                    and inspect.isclass(factory.dependency):
                wired.append(factory.dependency.__call__)
        else:
            wired.append(factory.function)

        header = HeaderObject(factory.header)
        return DependencyDebug(
            debug_repr(dependency),
            scope=header.to_scope(self._bound_container()),
            wired=wired,
            dependencies=dependencies)

    cdef fast_provide(self,
                      PyObject *dependency,
                      PyObject *container,
                      DependencyResult *result):
        cdef:
            PyObject *factory
            bint is_parameterized = PyObject_IsInstance(dependency, <PyObject *> Parameterized)
            PyObject *dependency_factory = (<PyObject *> (<Parameterized> dependency).wrapped
                                            if is_parameterized else
                                            dependency)

        if not PyObject_IsInstance(dependency_factory, <PyObject *> FactoryDependency):
            return

        factory = PyDict_GetItem(<PyObject *> self.__factories, dependency_factory)
        if factory is NULL:
            return

        if (<Factory> factory).function is None:
            (<RawContainer> container).fast_get(
                <PyObject *> (<Factory> factory).dependency,
                result)
            if result.value is NULL:
                raise DependencyNotFoundError((<Factory> factory).dependency)
            assert header_is_singleton(
                result.header), "factory dependency is expected to be a singleton"
            (<Factory> factory).function = <object> result.value
            Py_DECREF(result.value)

        if is_parameterized:
            result.header = (<Factory> factory).header
            result.value = PyObject_Call(
                <PyObject *> (<Factory> factory).function,
                <PyObject *> empty_tuple,
                <PyObject *> (<Parameterized> dependency).parameters
            )
        else:
            result.header = (<Factory> factory).header | header_flag_cacheable()
            result.value = PyObject_CallObject(
                <PyObject *> (<Factory> factory).function,
                NULL
            )

    def register(self,
                 output: type,
                 *,
                 Scope scope,
                 factory: Callable[..., object] = None,
                 factory_dependency: Hashable = None
                 ) -> FactoryDependency:
        cdef:
            Header header
            Factory f
        assert inspect.isclass(output) \
               and (factory is None or factory_dependency is None) \
               and (factory is None or callable(factory)) \
               and (isinstance(scope, Scope) or scope is None)
        with self._bound_container_ensure_not_frozen():
            dependency = FactoryDependency(output, factory or factory_dependency)
            self._bound_container_raise_if_exists(dependency)

            f = Factory.__new__(Factory)
            f.origin = <PyObject *> self
            f.header = HeaderObject.from_scope(scope).header
            if factory_dependency:
                f.dependency = factory_dependency
                f.function = None
            else:
                f.dependency = None
                f.function = factory
            self.__factories[dependency] = f
            return dependency

cdef class ClonedFactoryProvider(FactoryProvider):
    cdef:
        bint __keep_singletons_cache

    cdef object provider_type(self):
        return FactoryProvider

    cdef fast_provide(self,
                      PyObject *dependency,
                      PyObject *container,
                      DependencyResult *result):
        cdef:
            Factory f
            PyObject * factory
            bint is_parameterized = PyObject_IsInstance(dependency, <PyObject *> Parameterized)
            PyObject *dependency_factory = (<PyObject *> (<Parameterized> dependency).wrapped
                                            if is_parameterized else
                                            dependency)

        if not PyObject_IsInstance(dependency_factory, <PyObject *> FactoryDependency):
            return

        factory = PyDict_GetItem(<PyObject *> self.__factories, dependency_factory)
        if factory is NULL:
            return

        if (<Factory> factory).origin != <PyObject *> self \
                and (<Factory> factory).dependency is not None:
            f = Factory.__new__(Factory)
            f.origin = <PyObject *> self
            f.header = (<Factory> factory).header
            f.dependency = (<Factory> factory).dependency
            if self.__keep_singletons_cache:
                f.function = (<Factory> factory).function
            else:
                f.function = None
            PyDict_SetItem(<PyObject *> self.__factories, dependency_factory, <PyObject *> f)
            factory = <PyObject *> f

        if (<Factory> factory).function is None:
            (<RawContainer> container).fast_get(
                <PyObject *> (<Factory> factory).dependency,
                result)
            if result.value is NULL:
                raise DependencyNotFoundError((<Factory> factory).dependency)
            assert header_is_singleton(
                result.header), "factory dependency is expected to be a singleton"
            (<Factory> factory).function = <object> result.value
            Py_DECREF(result.value)

        if is_parameterized:
            result.header = (<Factory> factory).header
            result.value = PyObject_Call(
                <PyObject *> (<Factory> factory).function,
                <PyObject *> empty_tuple,
                <PyObject *> (<Parameterized> dependency).parameters
            )
        else:
            result.header = (<Factory> factory).header | header_flag_cacheable()
            result.value = PyObject_CallObject(
                <PyObject *> (<Factory> factory).function,
                NULL
            )

@cython.final
cdef class FactoryDependency:
    cdef:
        readonly object output
        readonly object factory
        Py_hash_t _hash

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

@cython.freelist(64)
@cython.final
cdef class Factory:
    cdef:
        Header header
        void * origin
        object function
        object dependency

    def __repr__(self):
        return (f"{type(self).__name__}(function={self.function}, "
                f"dependency={self.dependency})")
