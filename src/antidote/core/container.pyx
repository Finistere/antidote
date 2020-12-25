import threading
from collections import deque
from contextlib import contextmanager
from typing import (Any, Callable, Deque, Dict, Hashable, List, Mapping, Optional,
                    Tuple, Type)
from weakref import ref

# @formatter:off
cimport cython
from cpython.mem cimport PyMem_Free, PyMem_Malloc
from cpython.ref cimport PyObject
from fastrlock.rlock cimport create_fastrlock, lock_fastrlock, unlock_fastrlock

from antidote._internal.stack cimport DependencyStack
from .exceptions import (DependencyCycleError, DependencyInstantiationError,
                         DependencyNotFoundError, DuplicateDependencyError, FrozenWorldError)
# @formatter:on
from .utils import DependencyDebug


cdef extern from "Python.h":
    PyObject*PyList_GET_ITEM(PyObject *list, Py_ssize_t i)
    Py_ssize_t PyList_Size(PyObject *list)
    Py_ssize_t PyTuple_GET_SIZE(PyObject *p)
    int PyDict_SetItem(PyObject *p, PyObject *key, PyObject *val) except -1
    PyObject*PyDict_GetItem(PyObject *p, PyObject *key)


FLAG_DEFINED = 1
FLAG_SINGLETON = 2

@cython.freelist(64)
@cython.final
cdef class DependencyInstance:
    def __cinit__(self, value, *, bint singleton = False):
        self.value = value
        self.singleton = singleton

    def __repr__(self):
        return f"DependencyInstance(value={self.value}, singleton={self.singleton})"

    def __eq__(self, other):
        return isinstance(other, DependencyInstance) \
               and self.singleton == other.singleton \
               and self.value == other.value

@cython.freelist(64)
cdef class PyObjectBox:
    """
    Used to hold a Python object for DependencyResult. It is NOT initialized.
    """

cdef class Container:
    def get(self, dependency: Hashable):
        raise NotImplementedError()  # pragma: no cover

    def provide(self, dependency: Hashable):
        raise NotImplementedError()  # pragma: no cover

cdef class RawProvider:
    """
    Contrary to the Python implementation, the container does not rely on provide() but
    on fast_provide(). This is done to improve performance by avoiding object creation.
    """

    def __init__(self):
        self._container_ref = None

    def clone(self, keep_singletons_cache: bool) -> 'RawProvider':
        raise NotImplementedError()  # pragma: no cover

    def exists(self, dependency: Hashable) -> bool:
        raise NotImplementedError()  # pragma: no cover

    def maybe_debug(self, dependency: Hashable) -> Optional[DependencyDebug]:
        raise NotImplementedError()  # pragma: no cover

    def maybe_provide(self,
                      dependency: Hashable,
                      container: Container) -> DependencyInstance:
        raise NotImplementedError()

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        cdef:
            DependencyInstance dependency_instance
        dependency_instance = self.maybe_provide(<object> dependency,
                                                 <Container> container)
        if dependency_instance is not None:
            result.flags = FLAG_DEFINED | (
                FLAG_SINGLETON if dependency_instance.singleton else 0)
            (<PyObjectBox> result.box).obj = dependency_instance.value

    @contextmanager
    def _bound_container_ensure_not_frozen(self):
        container = self.__bound_container()
        if container is not None:
            with container.ensure_not_frozen():
                yield
        else:
            yield

    @contextmanager
    def _bound_container_locked(self):
        container = self.__bound_container()
        if container is not None:
            with container.locked():
                yield
        else:
            yield

    def _bound_container_raise_if_exists(self, dependency: Hashable):
        container = self.__bound_container()
        if container is not None:
            container.raise_if_exists(dependency)
        else:
            if self.exists(dependency):
                raise DuplicateDependencyError(
                    f"{dependency} has already been registered in {type(self)}")

    def __bound_container(self) -> 'Optional[RawContainer]':
        if self._container_ref is not None:
            container: RawContainer = self._container_ref()
            assert container is not None, "Associated container does not exist anymore."
            return container
        return None

    @property
    def is_registered(self):
        return self._container_ref is not None

cdef class FastProvider(RawProvider):
    def maybe_provide(self,
                      dependency: Hashable,
                      container: Container) -> DependencyInstance:
        cdef:
            DependencyResult result
            PyObjectBox box = PyObjectBox.__new__(PyObjectBox)
        result.box = <PyObject*> box

        result.flags = 0
        self.fast_provide(<PyObject*> dependency, <PyObject*> container, &result)
        if result.flags != 0:
            return DependencyInstance(box.obj,
                                      singleton=(result.flags & FLAG_SINGLETON) != 0)
        return None

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        raise NotImplementedError()

cdef class RawContainer(Container):
    """
    Behaves the same as the Python implementation but with additional optimizations:

    - singletons clock: Avoid testing twice the singleton dictionary it hasn't changed
                        since the first, not thread-safe, check.
    - cache: Recurring non singletons dependencies will not go through the usual _providers
             loop and their provider will be cached. This avoids the overhead of each
             provider checking whether it's a dependency it can provide or not.
    """

    def __init__(self, *, cache_size: int = 16):
        cdef:
            size_t capacity
            size_t*counter
        if not isinstance(cache_size, int):
            raise TypeError("cache_size must be a strictly positive integer.")
        if cache_size <= 0:
            raise ValueError("cache_size must be a strictly positive integer.")
        capacity = <size_t> cache_size

        self._providers = list()  # type: List[RawProvider]
        self._singletons = dict()  # type: dict
        self._dependency_stack = DependencyStack()
        self._instantiation_lock = create_fastrlock()
        self._freeze_lock = threading.RLock()
        self.__frozen = False

        # Cython optimizations
        self._singletons_clock = 0
        self.__cache.length = 0
        self.__cache.capacity = capacity
        self.__cache.dependencies = <PyObject**> PyMem_Malloc(
            capacity * sizeof(PyObject*))
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
        return f"{type(self).__name__}(_providers={', '.join(map(str, self._providers))})"

    @property
    def providers(self):
        return self._providers.copy()

    @contextmanager
    def locked(self):
        with self._freeze_lock, self._instantiation_lock:
            yield

    @contextmanager
    def ensure_not_frozen(self):
        with self._freeze_lock:
            if self.__frozen:
                raise FrozenWorldError()
            yield

    def freeze(self):
        with self._freeze_lock:
            self.__frozen = True

    def add_provider(self, provider_cls: Type[RawProvider]):
        cdef:
            RawProvider provider

        if not isinstance(provider_cls, type) \
            or not issubclass(provider_cls, RawProvider):
            raise TypeError(
                f"provider must be a Provider, not a {provider_cls}")

        with self.ensure_not_frozen(), self._instantiation_lock:
            if any(provider_cls == type(p) for p in self._providers):
                raise ValueError(f"Provider {provider_cls} already exists")

            provider = provider_cls()
            provider._container_ref = ref(self)
            self._providers.append(provider)
            self._singletons[provider_cls] = provider
            self._singletons_clock += 1

    def add_singletons(self, dependencies: Mapping):
        with self.ensure_not_frozen(), self._instantiation_lock:
            for k, v in dependencies.items():
                self.raise_if_exists(k)
            self._singletons.update(dependencies)
            self._singletons_clock += 1

    def raise_if_exists(self, dependency: Hashable):
        with self._freeze_lock:
            if dependency in self._singletons:
                raise DuplicateDependencyError(
                    f"{dependency!r} has already been defined as a singleton pointing "
                    f"to {self._singletons[dependency]}")

            for provider in self._providers:
                if provider.exists(dependency):
                    debug = provider.maybe_debug(dependency)
                    message = f"{dependency!r} has already been declared " \
                              f"in {type(provider)}"
                    if debug is None:
                        raise DuplicateDependencyError(message)
                    else:
                        raise DuplicateDependencyError(message + f"\n{debug.info}")

    def clone(self,
              *,
              keep_singletons: bool = False,
              clone_providers: bool = True) -> 'RawContainer':
        cdef:
            RawProvider clone
            RawProvider p
            RawContainer c = type(self)()

        with self._freeze_lock, self._instantiation_lock:
            if keep_singletons:
                c._singletons = self._singletons.copy()
            if clone_providers:
                for p in self._providers:
                    clone = p.clone(keep_singletons)
                    if clone is p or clone._container_ref is not None:
                        raise RuntimeError("A Provider should always return a fresh "
                                           "instance when copy() is called.")
                    clone._container_ref = ref(c)
                    c._providers.append(clone)
                    c._singletons[type(p)] = clone
            else:
                for p in self._providers:
                    c.add_provider(type(p))

        return c

    def debug(self, dependency: Hashable) -> DependencyDebug:
        from .._internal.utils.debug import debug_repr

        with self._freeze_lock:
            for p in self._providers:
                debug = p.maybe_debug(dependency)
                if debug is not None:
                    return debug
            try:
                value = self._singletons[dependency]
                return DependencyDebug(f"Singleton: {debug_repr(dependency)} "
                                       f"-> {value!r}",
                                       singleton=True)
            except KeyError:
                raise DependencyNotFoundError(dependency)

    def provide(self, dependency: Hashable):
        cdef:
            DependencyResult result
            PyObjectBox box = PyObjectBox.__new__(PyObjectBox)
        result.box = <PyObject*> box

        self.fast_get(<PyObject*> dependency, &result)
        if result.flags != 0:
            return DependencyInstance(box.obj,
                                      singleton=(result.flags & FLAG_SINGLETON) != 0)
        raise DependencyNotFoundError(dependency)

    def get(self, dependency: Hashable):
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
            unsigned long clock = self._singletons_clock

        result.flags = 0
        ptr = PyDict_GetItem(<PyObject*> self._singletons, dependency)
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
            object lock = self._instantiation_lock
            PyObject*singletons = <PyObject*> self._singletons
            PyObject*stack = <PyObject*> self._dependency_stack
            ProviderCache*cache
            PyObject** cached_dependency
            PyObject*providers
            size_t i

        lock_fastrlock(lock, -1, True)

        # If anything changed in the singletons the clock would be different
        # otherwise no need to re-check the dictionary.
        if singletons_clock < self._singletons_clock:
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
                    (<RawProvider> cache.providers[i]).fast_provide(
                        dependency, <PyObject*> self, result)
                    if result.flags != 0:
                        if (result.flags & FLAG_SINGLETON) != 0:
                            PyDict_SetItem(singletons,
                                           dependency,
                                           <PyObject*> (<PyObjectBox> result.box).obj)
                            self._singletons_clock += 1
                        elif i > 0:
                            cache_update(cache, i)
                        else:
                            cache.counters[i] += 1
                    return
                i += 1

            providers = <PyObject*> self._providers
            for i in range(<size_t> PyList_Size(providers)):
                (<RawProvider> PyList_GET_ITEM(providers, i)).fast_provide(
                    dependency,
                    <PyObject*> self,
                    result
                )
                if result.flags != 0:
                    if (result.flags & FLAG_SINGLETON) != 0:
                        PyDict_SetItem(singletons,
                                       dependency,
                                       <PyObject*> (<PyObjectBox> result.box).obj)
                        self._singletons_clock += 1
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

            if isinstance(error, DependencyInstantiationError):
                if (<DependencyStack> stack).depth == 1:
                    raise DependencyInstantiationError(<object> dependency) from error
                else:
                    raise
            raise DependencyInstantiationError(<object> dependency,
                                               (<DependencyStack> stack).to_list()[1:]) from error
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

cdef class OverridableRawContainer(RawContainer):
    cdef:
        object __override_lock
        dict __singletons_override
        dict __factory_overrides
        object __provider_overrides


    def __init__(self):
        super().__init__()
        self.__override_lock = threading.RLock()
        # Used to differentiate singletons from the overrides and the "normal" ones.
        self.__singletons_override = dict()
        self.__factory_overrides: Dict[Any, Tuple[Callable[[], Any], bool]] = {}
        self.__provider_overrides: Deque[
            Callable[[Any], Optional[DependencyInstance]]] = deque()

    @classmethod
    def build(cls,
              original: RawContainer,
              keep_singletons: bool) -> 'OverridableRawContainer':
        cdef:
            RawContainer clone = original.clone(keep_singletons=keep_singletons)
            OverridableRawContainer container = OverridableRawContainer()

        container._singletons = clone._singletons
        container._providers = clone._providers
        if isinstance(clone, OverridableRawContainer):
            container.__singletons_override = (
                <OverridableRawContainer> clone).__singletons_override
            container.__factory_overrides = (
                <OverridableRawContainer> clone).__factory_overrides
            container.__provider_overrides = (
                <OverridableRawContainer> clone).__provider_overrides
        return container

    def override_singletons(self, singletons: dict):
        if not isinstance(singletons, dict):
            raise TypeError(f"singletons must be a dict, not a {type(singletons)}")
        with self.__override_lock:
            self.__singletons_override.update(singletons)

    def override_factory(self,
                         dependency: Hashable,
                         *,
                         factory: Callable[[], Any],
                         singleton: bool):
        if not callable(factory):
            raise TypeError(f"factory must be a callable, not a {type(factory)}")
        if not isinstance(singleton, bool):
            raise TypeError(f"singleton must be a boolean, not a {type(singleton)}")
        with self.__override_lock:
            self.__factory_overrides[dependency] = (factory, singleton)

    def override_provider(self,
                          provider: Callable[[Any], Optional[DependencyInstance]]):
        if not callable(provider):
            raise TypeError(f"provider must be a callable, not a {type(provider)}")
        with self.__override_lock:
            self.__provider_overrides.appendleft(provider)  # latest provider wins

    def clone(self,
              *,
              keep_singletons: bool = False,
              clone_providers: bool = True) -> 'OverridableRawContainer':
        cdef:
            OverridableRawContainer container

        with self.__override_lock:
            container = super().clone(keep_singletons=keep_singletons,
                                      clone_providers=clone_providers)
            if keep_singletons:
                container.__singletons_override = self.__singletons_override.copy()
            container.__factory_overrides = self.__factory_overrides.copy()
            container.__provider_overrides = self.__provider_overrides.copy()

        return container

    def debug(self, dependency: Hashable) -> DependencyDebug:
        from .._internal.utils.debug import debug_repr

        with self.__override_lock:
            try:
                value = self.__singletons_override[dependency]
            except KeyError:
                pass
            else:
                return DependencyDebug(f"Override/Singleton: {debug_repr(dependency)} "
                                       f"-> {value!r}",
                                       singleton=True)
            try:
                (factory, singleton) = self.__factory_overrides[dependency]
            except KeyError:
                pass
            else:
                return DependencyDebug(f"Override/Factory: {debug_repr(dependency)} "
                                       f"-> {debug_repr(factory)}",
                                       singleton=singleton)

        return super().debug(dependency)

    # Less efficient than the original fast_get, but we don't really care in tests.
    cdef fast_get(self, PyObject*dependency, DependencyResult*result):
        cdef:
            PyObject*ptr
            PyObjectBox box

        dep = <object> dependency
        result.flags = 0
        with self.__override_lock, self._instantiation_lock:
            with self._dependency_stack.instantiating(dep):
                try:
                    obj = self.__singletons_override[dep]
                except KeyError:
                    pass
                else:
                    result.flags = FLAG_DEFINED | FLAG_SINGLETON
                    (<PyObjectBox> result.box).obj = obj
                    return

                try:
                    for provider in self.__provider_overrides:
                        dependency_instance = provider(dep)
                        if dependency_instance is not None:
                            if dependency_instance.singleton:
                                self.__singletons_override[
                                    dep] = dependency_instance.value
                                result.flags = FLAG_DEFINED | FLAG_SINGLETON
                            else:
                                result.flags = FLAG_DEFINED
                            (<PyObjectBox> result.box).obj = dependency_instance.value
                            return

                    try:
                        (factory, singleton) = self.__factory_overrides[dep]
                    except KeyError:
                        pass
                    else:
                        obj = factory()
                        if singleton:
                            self.__singletons_override[dep] = obj
                            result.flags = FLAG_DEFINED | FLAG_SINGLETON
                        else:
                            result.flags = FLAG_DEFINED
                        (<PyObjectBox> result.box).obj = obj
                        return

                except Exception as error:
                    if isinstance(error, DependencyCycleError):
                        raise
                    raise DependencyInstantiationError(<object> dependency) from error

            RawContainer.fast_get(self, dependency, result)
