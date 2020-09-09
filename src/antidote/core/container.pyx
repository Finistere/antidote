# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False
from typing import Any, Dict, Hashable, List, Mapping

# @formatter:off
cimport cython
from cpython.mem cimport PyMem_Malloc, PyMem_Free
from cpython.ref cimport PyObject
from fastrlock.rlock cimport create_fastrlock, lock_fastrlock, unlock_fastrlock

from antidote._internal.stack cimport DependencyStack
# @formatter:on
from .exceptions import (DependencyCycleError, DependencyInstantiationError,
                         DependencyNotFoundError, FrozenWorldError)

cdef extern from "Python.h":
    PyObject* PyList_GET_ITEM(PyObject *list, Py_ssize_t i)
    Py_ssize_t PyList_Size(PyObject *list)
    Py_ssize_t PyTuple_GET_SIZE(PyObject *p)
    int PyDict_SetItem(PyObject *p, PyObject *key, PyObject *val) except -1
    PyObject* PyDict_GetItem(PyObject *p, PyObject *key)


FLAG_DEFINED = 1
FLAG_SINGLETON = 2

@cython.freelist(32)
cdef class DependencyInstance:
    """
    Simple wrapper used by a :py:class:`~.core.DependencyProvider` when returning
    an instance of a dependency so it can specify in which scope the instance
    belongs to.
    """
    def __cinit__(self, object instance, bint singleton = False):
        self.instance = instance
        self.singleton = singleton

    def __repr__(self):
        return f"{type(self).__name__}(instance={self.instance!r}, singleton={self.singleton!r})"

    cdef DependencyInstance copy(self):
        return DependencyInstance.__new__(DependencyInstance,
                                          self.instance,
                                          self.singleton)

@cython.freelist(64)
cdef class PyObjectBox:
    def __cinit__(self):
        self.obj = None

@cython.final
cdef class DependencyContainer:
    """
    Instantiates the dependencies through the registered providers and handles
    their scope.
    """

    def __init__(self):
        cdef:
            size_t capacity = 16
            size_t* counter

        self.__providers = list()  # type: List[DependencyProvider]
        self.__singletons = dict()  # type: Dict[Any, Any]
        self.__singletons[DependencyContainer] = self
        self.__dependency_stack = DependencyStack()
        self.__instantiation_lock = create_fastrlock()
        self.__singletons_clock = 0
        self.__frozen = False

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

    def __str__(self):
        return f"{type(self).__name__}(providers={', '.join(map(str, self.__providers))})"

    def __repr__(self):
        return f"{type(self).__name__}(providers={', '.join(map(str, self.__providers))}, " \
               f"singletons={self.__singletons!r})"

    def freeze(self):
        with self.__instantiation_lock:
            self.__frozen = True
            for provider in self.__providers:
                provider.freeze()

    def clone(self, keep_singletons: bool = False) -> 'DependencyContainer':
        c = DependencyContainer()
        with self.__instantiation_lock:
            c.__singletons = self.__singletons.copy() if keep_singletons else dict()
            c.__providers = [p.clone() for p in self.__providers]
            c.__singletons[DependencyContainer] = c
            for p in c.__providers:
                c.__singletons[type(p)] = p
        return c

    def register_provider(self, provider: Hashable):
        """
        Registers a provider, which can then be used to instantiate dependencies.

        Args:
            provider: Provider instance to be registered.

        """
        if not isinstance(provider, DependencyProvider):
            raise TypeError(
                f"provider must be a DependencyProvider, not a {type(provider)!r}")

        with self.__instantiation_lock:
            if self.__frozen:
                raise FrozenWorldError(f"Cannot add provider {type(provider)} "
                                       f"to a frozen container.")
            self.__providers.append(provider)
            self.__singletons[type(provider)] = provider
            self.__singletons_clock += 1

    def update_singletons(self, dependencies: Mapping):
        """
        Update the singletons.
        """
        with self.__instantiation_lock:
            if self.__frozen:
                raise FrozenWorldError(f"Cannot add singletons to a frozen container. "
                                       f"singletons = {dependencies}")
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
        """
        Returns an instance for the given dependency. All registered providers
        are called sequentially until one returns an instance.  If none is
        found, :py:exc:`~.exceptions.DependencyNotFoundError` is raised.

        Args:
            dependency: Passed on to the registered providers.

        Returns:
            instance for the given dependency
        """
        cdef:
            DependencyResult result
            PyObjectBox box = PyObjectBox.__new__(PyObjectBox)
        result.box = <PyObject*> box

        self.fast_get(<PyObject*> dependency, &result)
        if result.flags != 0:
            return box.obj
        raise DependencyNotFoundError(dependency)

    # No ownership from here on. You MUST keep a valid reference to dependency.
    cdef fast_get(self, PyObject* dependency, DependencyResult* result):
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
                        PyObject* dependency,
                        DependencyResult* result,
                        unsigned long singletons_clock):
        cdef:
            PyObject* ptr
            Exception error
            object lock = self.__instantiation_lock
            PyObject* singletons = <PyObject*> self.__singletons
            PyObject* stack = <PyObject*> self.__dependency_stack
            ProviderCache* cache
            PyObject** cached_dependency
            PyObject* providers
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

        if 0 != (<DependencyStack> stack).push(dependency):
            error = (<DependencyStack> stack).reset_with_error(dependency)
            unlock_fastrlock(lock)
            raise error

        try:
            cache = &self.__cache
            i = 0
            for cached_dependency in cache.dependencies[:cache.length]:
                if dependency == cached_dependency[0]:
                    (<DependencyProvider> cache.providers[i]).fast_provide(
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
                        elif i > 0:
                            cache_update(cache, i)
                        else:
                            cache.counters[i] += 1
                    return
                i += 1

            providers = <PyObject*> self.__providers
            for i in range(<size_t> PyList_Size(providers)):
                (<DependencyProvider> PyList_GET_ITEM(providers, i)).fast_provide(
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
cdef inline void cache_update(ProviderCache* cache, size_t pos) nogil:
    cdef:
        size_t counter, i = pos, new_pos = 0
        PyObject* provider
        PyObject* dependency
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

cdef class DependencyProvider:
    """
    Abstract base class for a Provider.

    Used by the :py:class:`~.core.DependencyContainer` to instantiate
    dependencies. Several are used in a cooperative manner : the first instance
    to be returned by one of them is used. Thus providers should ideally not
    overlap and handle only one kind of dependencies such as strings or tag.

    This should be used whenever one needs to introduce a new kind of dependency,
    or control how certain dependencies are instantiated.
    """

    def world_provide(self, dependency: Hashable):
        """
        Method only used for tests to avoid the repeated injection of the current
        DependencyContainer.
        """
        from antidote import world
        return self.provide(dependency, world.get(DependencyContainer))

    cdef fast_provide(self,
                      PyObject* dependency,
                      PyObject* container,
                      DependencyResult* result):
        cdef:
            DependencyInstance dependency_instance

        dependency_instance = self.provide(<object> dependency, <DependencyContainer> container)
        if dependency_instance is not None:
            result.flags = FLAG_DEFINED | (FLAG_SINGLETON if dependency_instance.singleton else 0)
            (<PyObjectBox> result.box).obj = dependency_instance.instance

    cpdef DependencyInstance provide(self,
                                     object dependency: Hashable,
                                     DependencyContainer container):
        """
        Method called by the :py:class:`~.core.DependencyContainer` when
        searching for a dependency.

        It is necessary to check quickly if the dependency can be provided or
        not, as :py:class:`~.core.DependencyContainer` will try its
        registered providers. A good practice is to subclass
        :py:class:`~.core.Dependency` so custom dependencies be differentiated.

        Args:
            dependency: The dependency to be provided by the provider.
            container: current container

        Returns:
            The requested instance wrapped in a :py:class:`~.core.Instance`
            if available or :py:obj:`None`.
        """
        raise NotImplementedError()

    def clone(self) -> 'DependencyProvider':
        raise NotImplementedError()

    def freeze(self):
        raise NotImplementedError()

cdef class FastDependencyProvider(DependencyProvider):
    cpdef DependencyInstance provide(self,
                                     object dependency: Hashable,
                                     DependencyContainer container):
        cdef:
            DependencyResult result
            PyObjectBox box = PyObjectBox.__new__(PyObjectBox)
        result.box = <PyObject*> box

        self.fast_provide(<PyObject*> dependency, <PyObject*> container, &result)
        if result.flags != 0:
            return DependencyInstance.__new__(
                DependencyInstance,
                box.obj,
                (result.flags & FLAG_SINGLETON) != 0
            )
        return None

    cdef fast_provide(self,
                      PyObject* dependency,
                      PyObject* container,
                      DependencyResult* result):
        raise NotImplementedError()
