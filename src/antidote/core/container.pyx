import threading
from contextlib import contextmanager
from typing import Any, Dict, Hashable, List, Mapping, Type
from weakref import ref

# @formatter:off
cimport cython
from cpython.mem cimport PyMem_Malloc, PyMem_Free
from cpython.ref cimport PyObject
from fastrlock.rlock cimport create_fastrlock, lock_fastrlock, unlock_fastrlock

from antidote._internal.stack cimport DependencyStack
from .exceptions import (DependencyCycleError, DependencyInstantiationError,
                         DependencyNotFoundError, FrozenContainerError)

# @formatter:on


cdef extern from "Python.h":
    PyObject*PyList_GET_ITEM(PyObject *list, Py_ssize_t i)
    Py_ssize_t PyList_Size(PyObject *list)
    Py_ssize_t PyTuple_GET_SIZE(PyObject *p)
    int PyDict_SetItem(PyObject *p, PyObject *key, PyObject *val) except -1
    PyObject*PyDict_GetItem(PyObject *p, PyObject *key)


FLAG_DEFINED = 1
FLAG_SINGLETON = 2

@cython.freelist(32)
cdef class DependencyInstance:
    def __cinit__(self, object instance, bint singleton = False):
        self.instance = instance
        self.singleton = singleton

    def __repr__(self):
        return f"{type(self).__name__}(instance={self.instance!r}, singleton={self.singleton!r})"

@cython.freelist(64)
cdef class PyObjectBox:
    """
    Used to hold a Python object for DependencyResult. It is NOT initialized.
    """

cdef class DependencyContainer:
    cpdef object get(self, dependency: Hashable):
        raise NotImplementedError()  # pragma: no cover

    cpdef DependencyInstance provide(self, dependency: Hashable):
        raise NotImplementedError()  # pragma: no cover

    @contextmanager
    def ensure_not_frozen(self):
        raise NotImplementedError()  # pragma: no cover

cdef class RawDependencyProvider:
    """
    Contrary to the Python implementation, the container does not rely on provide() but
    on fast_provide(). This is done to improve performance by avoiding object creation.
    """

    def __init__(self):
        self._container_ref = None

    cpdef DependencyInstance provide(self,
                                     object dependency: Hashable,
                                     DependencyContainer container):
        raise NotImplementedError()

    def copy(self) -> 'RawDependencyProvider':
        raise NotImplementedError()  # pragma: no cover

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        cdef:
            DependencyInstance dependency_instance

        dependency_instance = self.provide(<object> dependency, <DependencyContainer> container)
        if dependency_instance is not None:
            result.flags = FLAG_DEFINED | (FLAG_SINGLETON if dependency_instance.singleton else 0)
            (<PyObjectBox> result.box).obj = dependency_instance.instance

    @contextmanager
    def _ensure_not_frozen(self):
        if self._container_ref is None:
            yield
        else:
            container = self._container_ref()
            assert container is not None
            with container.ensure_not_frozen():
                yield

cdef class FastDependencyProvider(RawDependencyProvider):
    cpdef DependencyInstance provide(self,
                                     object dependency: Hashable,
                                     DependencyContainer container):
        cdef:
            DependencyResult result
            PyObjectBox box = PyObjectBox.__new__(PyObjectBox)
        result.box = <PyObject*> box

        result.flags = 0
        self.fast_provide(<PyObject*> dependency, <PyObject*> container, &result)
        if result.flags != 0:
            return DependencyInstance.__new__(
                DependencyInstance,
                box.obj,
                (result.flags & FLAG_SINGLETON) != 0
            )
        return None

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        raise NotImplementedError()

@cython.final
cdef class RawDependencyContainer(DependencyContainer):
    """
    Behaves the same as the Python implementation but with additional optimizations:
    - singletons clock: Avoid testing twice the singleton dictionary it hasn't changed
                        since the first, not thread-safe, check.
    - cache: Recurring non singletons dependencies will not go through the usual providers
             loop and their provider will be cached. This avoids the overhead of each
             provider checking whether it's a dependency it can provide or not.
    """

    def __init__(self, cache_size: int = 16):
        cdef:
            size_t capacity
            size_t*counter
        if not isinstance(cache_size, int):
            raise TypeError("cache_size must be a strictly positive integer.")
        if cache_size <= 0:
            raise ValueError("cache_size must be a strictly positive integer.")
        capacity = <size_t> cache_size

        self.__providers = list()  # type: List[RawDependencyProvider]
        self.__singletons = dict()  # type: Dict[Any, Any]
        self.__dependency_stack = DependencyStack()
        self.__singleton_lock = create_fastrlock()
        self.__freeze_lock = threading.RLock()
        self.__frozen = False

        # Cython optimizations
        self.__singletons_clock = 0
        self.__cache.length = 0
        self.__cache.capacity = capacity
        self.__cache.dependencies = <PyObject**> PyMem_Malloc(capacity * sizeof(PyObject*))
        self.__cache.providers = <PyObject**> PyMem_Malloc(capacity * sizeof(PyObject*))
        self.__cache.counters = <size_t*> PyMem_Malloc(capacity * sizeof(size_t))
        if not self.__cache.dependencies or not self.__cache.providers or not self.__cache.counters:
            raise MemoryError()
        for counter in self.__cache.counters[:capacity]:
            counter[0] = 0

    def __dealloc__(self):
        PyMem_Free(self.__cache.dependencies)
        PyMem_Free(self.__cache.providers)
        PyMem_Free(self.__cache.counters)

    def __repr__(self):
        return f"{type(self).__name__}(providers={', '.join(map(str, self.__providers))})"

    @contextmanager
    def ensure_not_frozen(self):
        with self.__freeze_lock:
            if self.__frozen:
                raise FrozenContainerError()
            yield

    @property
    def providers(self):
        return [p for p in self.__providers]

    def freeze(self):
        with self.__freeze_lock:
            self.__frozen = True

    def clone(self,
              *,
              keep_singletons: bool = False,
              clone_providers: bool = True) -> 'RawDependencyContainer':
        cdef:
            RawDependencyProvider clone, p
            RawDependencyContainer c

        c = RawDependencyContainer()
        with self.__singleton_lock:
            if keep_singletons:
                c.__singletons = self.__singletons.copy()
            if clone_providers:
                for p in self.__providers:
                    clone = p.copy()
                    if clone is p or clone._container_ref is not None:
                        raise RuntimeError("A Provider should always return a fresh "
                                           "instance when copy() is called.")
                    clone._container_ref = ref(c)
                    c.__providers.append(clone)
                    c.__singletons[type(p)] = clone
            else:
                for p in self.__providers:
                    c.register_provider(type(p))

        return c

    def register_provider(self, provider_cls: Type[RawDependencyProvider]):
        cdef:
            RawDependencyProvider provider

        if not isinstance(provider_cls, type) \
                or not issubclass(provider_cls, RawDependencyProvider):
            raise TypeError(
                f"provider must be a DependencyProvider, not a {provider_cls}")

        with self.ensure_not_frozen(), self.__singleton_lock:
            if any(provider_cls == type(p) for p in self.__providers):
                raise ValueError(f"Provider {provider_cls} already exists")

            provider = provider_cls()
            provider._container_ref = ref(self)
            self.__providers.append(provider)
            self.__singletons[provider_cls] = provider
            self.__singletons_clock += 1

    def update_singletons(self, dependencies: Mapping):
        with self.ensure_not_frozen(), self.__singleton_lock:
            self.__singletons.update(dependencies)
            self.__singletons_clock += 1

    cpdef DependencyInstance provide(self, dependency: Hashable):
        cdef:
            DependencyResult result
            PyObjectBox box = PyObjectBox.__new__(PyObjectBox)
        result.box = <PyObject*> box

        self.fast_get(<PyObject*> dependency, &result)
        if result.flags != 0:
            return DependencyInstance.__new__(
                DependencyInstance,
                box.obj,
                (result.flags & FLAG_SINGLETON) != 0
            )
        raise DependencyNotFoundError(dependency)

    cpdef object get(self, dependency: Hashable):
        cdef:
            DependencyResult result
            PyObjectBox box = PyObjectBox.__new__(PyObjectBox)
        result.box = <PyObject*> box

        self.fast_get(<PyObject*> dependency, &result)
        if result.flags != 0:
            return box.obj
        raise DependencyNotFoundError(dependency)

    # No ownership from here on. You MUST keep a valid reference to dependency.
    cdef fast_get(self, PyObject*dependency, DependencyResult*result):
        cdef:
            PyObject*ptr
            PyObjectBox box
            unsigned long clock = self.__singletons_clock

        result.flags = 0
        ptr = PyDict_GetItem(<PyObject*> self.__singletons, dependency)
        if ptr != NULL:
            result.flags = FLAG_DEFINED | FLAG_SINGLETON
            (<PyObjectBox> result.box).obj = <object> ptr
        else:
            self.__safe_provide(dependency, result, clock)

    cdef __safe_provide(self,
                        PyObject*dependency,
                        DependencyResult*result,
                        unsigned long singletons_clock):
        cdef:
            PyObject*ptr
            Exception error
            object lock = self.__singleton_lock
            PyObject*singletons = <PyObject*> self.__singletons
            PyObject*stack = <PyObject*> self.__dependency_stack
            ProviderCache*cache
            PyObject** cached_dependency
            PyObject*providers
            size_t i

        lock_fastrlock(lock, -1, True)

        # If anything changed in the singletons the clock would be different
        # otherwise no need to re-check the dictionary.
        if singletons_clock < self.__singletons_clock:
            ptr = PyDict_GetItem(singletons, dependency)
            if ptr != NULL:
                unlock_fastrlock(lock)
                result.flags = FLAG_DEFINED | FLAG_SINGLETON
                (<PyObjectBox> result.box).obj = <object> ptr
                return

        if 0 != (<DependencyStack> stack).push(dependency):
            error = (<DependencyStack> stack).reset_with_error(dependency)
            unlock_fastrlock(lock)
            raise error

        try:
            cache = &self.__cache
            i = 0
            for cached_dependency in cache.dependencies[:cache.length]:
                if dependency == cached_dependency[0]:
                    (<RawDependencyProvider> cache.providers[i]).fast_provide(
                        dependency, <PyObject*> self, result)
                    if result.flags != 0:
                        if (result.flags & FLAG_SINGLETON) != 0:
                            PyDict_SetItem(singletons,
                                           dependency,
                                           <PyObject*> (<PyObjectBox> result.box).obj)
                            self.__singletons_clock += 1
                        elif i > 0:
                            cache_update(cache, i)
                        else:
                            cache.counters[i] += 1
                    return
                i += 1

            providers = <PyObject*> self.__providers
            for i in range(<size_t> PyList_Size(providers)):
                (<RawDependencyProvider> PyList_GET_ITEM(providers, i)).fast_provide(
                    dependency,
                    <PyObject*> self,
                    result
                )
                if result.flags != 0:
                    if (result.flags & FLAG_SINGLETON) != 0:
                        PyDict_SetItem(singletons,
                                       dependency,
                                       <PyObject*> (<PyObjectBox> result.box).obj)
                        self.__singletons_clock += 1
                    else:
                        if cache.length < cache.capacity:
                            cache.length += 1
                        ptr = PyList_GET_ITEM(providers, i)
                        i = cache.length - 1
                        cache.providers[i] = ptr
                        cache.dependencies[i] = dependency
                        cache_update(cache, i)
                    return

        except Exception as error:
            if isinstance(error, DependencyCycleError):
                raise
            raise DependencyInstantiationError(<object> dependency) from error
        finally:
            (<DependencyStack> stack).pop()
            unlock_fastrlock(lock)

# Imitating the SpaceSaving algorithm
cdef inline void cache_update(ProviderCache*cache, size_t pos) nogil:
    cdef:
        size_t counter, i = pos, new_pos = 0
        PyObject*provider
        PyObject*dependency
    counter = cache.counters[pos] + 1
    while 0 < i:
        i -= 1
        if counter < cache.counters[i]:
            new_pos = i + 1
            break

    if pos != new_pos:
        dependency = cache.dependencies[pos]
        provider = cache.providers[pos]
        cache.dependencies[pos] = cache.dependencies[new_pos]
        cache.counters[pos] = cache.counters[new_pos]
        cache.providers[pos] = cache.providers[new_pos]
        cache.dependencies[new_pos] = dependency
        cache.providers[new_pos] = provider
    cache.counters[new_pos] = counter
