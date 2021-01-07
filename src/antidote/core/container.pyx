import threading
from collections import deque
from contextlib import contextmanager
from typing import (Any, Callable, Deque, Dict, Hashable, List, Mapping, Optional,
                    Tuple, Type)
from weakref import ref

# @formatter:off
cimport cython
from fastrlock.rlock cimport create_fastrlock, lock_fastrlock, unlock_fastrlock
from cpython.mem cimport PyMem_Free, PyMem_Malloc
from cpython.ref cimport Py_XINCREF, PyObject, Py_XDECREF

from antidote._internal.stack cimport DependencyStack
from .exceptions import (DependencyCycleError, DependencyInstantiationError,
                         DependencyNotFoundError, DuplicateDependencyError, FrozenWorldError)
# @formatter:on

cdef extern from "Python.h":
    PyObject*PyList_GET_ITEM(PyObject *list, Py_ssize_t i)
    Py_ssize_t PyList_Size(PyObject *list)
    Py_ssize_t PyTuple_GET_SIZE(PyObject *p)
    int PyDict_SetItem(PyObject *p, PyObject *key, PyObject *val) except -1
    PyObject*PyDict_GetItem(PyObject *p, PyObject *key)


##############
# Dependency #
##############

DEF HEADER_FLAG_NO_SCOPE = 0
DEF HEADER_FLAG_SINGLETON = 1
DEF HEADER_FLAG_HAS_SCOPE = 2
DEF HEADER_FLAG_CACHEABLE = 4

cdef inline ScopeId header_get_scope_id(Header header):
    return header >> 8

cdef inline Header header_scope(ScopeId scope_id):
    return HEADER_FLAG_HAS_SCOPE | ((scope_id & 0xFF) << 8)

# Utilities outside of container.pyx

cdef bint header_is_singleton(Header header):
    return (header & HEADER_FLAG_SINGLETON) == HEADER_FLAG_SINGLETON

cdef bint header_has_scope(Header header):
    return (header & HEADER_FLAG_HAS_SCOPE) == HEADER_FLAG_HAS_SCOPE

cdef bint header_is_cacheable(Header header):
    return (header & HEADER_FLAG_CACHEABLE) == HEADER_FLAG_CACHEABLE

cdef Header header_strictest(Header h1, Header h2):
    if (h1 >> 8) == (h2 >> 8):
        return h1 & h2
    return HEADER_FLAG_NO_SCOPE

cdef Header header_flag_singleton():
    return HEADER_FLAG_SINGLETON

cdef Header header_flag_no_scope():
    return HEADER_FLAG_NO_SCOPE

cdef Header header_flag_cacheable():
    return HEADER_FLAG_CACHEABLE


@cython.final
cdef class Scope:
    def __init__(self, str name):
        self.name = name

    def __repr__(self):
        return f"Scope(name='{self.name}')"

    @staticmethod
    def singleton():
        return _SCOPE_SINGLETON

    @staticmethod
    def sentinel():
        return _SCOPE_SENTINEL

_SCOPE_SINGLETON = Scope('singleton')
_SCOPE_SENTINEL = Scope('__sentinel__')


cdef class HeaderObject:
    """
    Utility wrapper for maybe_debug() and in case the header needs to be wrapped inside
    an object (dict values in service for example)
    """
    def __cinit__(self, Header header):
        self.header = header

    @staticmethod
    cdef HeaderObject from_scope(Scope scope):
        if scope is None:
            return HeaderObject.__new__(HeaderObject, HEADER_FLAG_NO_SCOPE)
        if scope is _SCOPE_SINGLETON:
            return HeaderObject.__new__(HeaderObject, HEADER_FLAG_SINGLETON)
        return HeaderObject.__new__(HeaderObject, header_scope(scope.id))

    def to_scope(self, RawContainer container) -> Optional[Scope]:
        scope = None
        if self.is_singleton():
            scope = _SCOPE_SINGLETON
        elif self.has_scope():
            scope = container.get_scope(self.get_scope_id())
        return scope

    def is_singleton(self):
        return header_is_singleton(self.header)

    def has_scope(self):
        return header_has_scope(self.header)

    def get_scope_id(self):
        return header_get_scope_id(self.header)

    def is_cacheable(self):
        return header_is_cacheable(self.header)


@cython.freelist(64)
@cython.final
cdef class DependencyInstance:
    def __cinit__(self, value, *, Scope scope = None):
        assert scope is not _SCOPE_SENTINEL
        self.value = value
        self.scope = scope

    def __repr__(self):
        return f"DependencyInstance(value={self.value}, singleton={self.singleton})"

    def __eq__(self, other):
        return isinstance(other, DependencyInstance) \
               and self.value == other.value \
               and self.scope == other.scope

    def is_singleton(self) -> bool:
        return self.scope is _SCOPE_SINGLETON

    cdef to_result(self, DependencyResult *result):
        result.header = HeaderObject.from_scope(self.scope).header
        result.value = <PyObject*> self.value
        Py_XINCREF(result.value)

cdef DependencyInstance build_dependency_instance(RawContainer container,
                                                  DependencyResult *result):
    scope = HeaderObject(result.header).to_scope(container)
    value = <object> result.value
    Py_XDECREF(result.value)
    return DependencyInstance.__new__(DependencyInstance,
                                      value,
                                      scope=scope)

############
# PROVIDER #
############

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

    def maybe_debug(self, dependency: Hashable):
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
            dependency_instance.to_result(result)

    @contextmanager
    def _bound_container_ensure_not_frozen(self):
        container = self._bound_container()
        if container is not None:
            with container.ensure_not_frozen():
                yield
        else:
            yield

    @contextmanager
    def _bound_container_locked(self):
        container = self._bound_container()
        if container is not None:
            with container.locked():
                yield
        else:
            yield

    def _bound_container_raise_if_exists(self, dependency: Hashable):
        container = self._bound_container()
        if container is not None:
            container.raise_if_exists(dependency)
        else:
            if self.exists(dependency):
                raise DuplicateDependencyError(
                    f"{dependency} has already been registered in {type(self)}")

    cdef RawContainer _bound_container(self):
        if self._container_ref is not None:
            container = self._container_ref()
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
        result.value = NULL
        self.fast_provide(<PyObject*> dependency, <PyObject*> container, &result)
        if result.value:
            return build_dependency_instance(self._bound_container(), &result)
        return None

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        raise NotImplementedError()

#############
# CONTAINER #
#############

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
        self._is_clone = False
        self.__frozen = False
        self._scopes = []
        self._scope_dependencies = []  # type: List[dict]

        # Cython optimizations
        self.__singletons_clock = 0
        self.__cache = DependencyCache()

    def __repr__(self):
        return f"{type(self).__name__}(_providers={', '.join(map(str, self._providers))})"

    @property
    def is_clone(self):
        return self._is_clone

    def create_scope(self, str name):
        cdef:
            Scope s = Scope(name)
        s.id = <ScopeId> (1 + len(self._scopes))
        assert s.id <= 0xFF
        assert all(s.name != name for s in self._scopes)
        self._scopes.append(s)
        self._scope_dependencies.append(dict())
        return s

    def reset_scope(self, Scope scope):
        self._scope_dependencies[scope.id - 1] = dict()

    cdef Scope get_scope(self, ScopeId scope_id):
        return <Scope> self._scopes[scope_id - 1]

    @property
    def scopes(self):
        return self._scopes.copy()

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
        with self.ensure_not_frozen(), self._instantiation_lock:
            assert all(provider_cls != type(p) for p in self._providers)
            provider = provider_cls()
            provider._container_ref = ref(self)
            self._providers.append(provider)
            (<DependencyCache> self.__cache).set(<PyObject*> provider_cls,
                                                 HEADER_FLAG_SINGLETON,
                                                 <PyObject*> provider)
            self.__singletons_clock += 1

    def add_singletons(self, dependencies: Mapping):
        with self.ensure_not_frozen(), self._instantiation_lock:
            for k, v in dependencies.items():
                self.raise_if_exists(k)
            for k, v in dependencies.items():
                (<DependencyCache> self.__cache).set(<PyObject*> k,
                                                     HEADER_FLAG_SINGLETON,
                                                     <PyObject*> v)
            self._singletons.update(dependencies)
            self.__singletons_clock += 1

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
              keep_singletons: bool,
              keep_scopes: bool) -> 'RawContainer':
        cdef:
            RawProvider clone
            RawProvider p
            RawContainer c = type(self)()

        c._is_clone = True
        with self._freeze_lock, self._instantiation_lock:
            # clone is only used for tests, so don't really care about the cache.
            if keep_singletons:
                c._singletons = self._singletons.copy()

            c._scopes = self._scopes
            c._scope_dependencies = [
                d.copy() if keep_scopes else dict()
                for d in self._scope_dependencies
            ]

            for p in self._providers:
                clone = p.clone(keep_singletons)
                if clone is p or clone._container_ref is not None:
                    raise RuntimeError("A Provider should always return a fresh "
                                       "instance when copy() is called.")
                clone._container_ref = ref(c)
                c._providers.append(clone)
                c._singletons[type(p)] = clone

        return c

    def debug(self, dependency: Hashable):
        from .._internal.utils.debug import debug_repr
        from .utils import DependencyDebug

        with self._freeze_lock:
            for p in self._providers:
                debug = p.maybe_debug(dependency)
                if debug is not None:
                    return debug
            try:
                value = self._singletons[dependency]
                return DependencyDebug(f"Singleton: {debug_repr(dependency)} "
                                       f"-> {value!r}",
                                       scope=Scope.singleton())
            except KeyError:
                raise DependencyNotFoundError(dependency)

    def provide(self, dependency: Hashable):
        cdef:
            DependencyResult result

        self.fast_get(<PyObject*> dependency, &result)
        if result.value:
            return build_dependency_instance(self, &result)
        raise DependencyNotFoundError(dependency)

    def get(self, dependency: Hashable):
        cdef:
            DependencyResult result
            object obj

        self.fast_get(<PyObject*> dependency, &result)
        if result.value:
            obj = <object> result.value
            Py_XDECREF(result.value)
            return obj
        raise DependencyNotFoundError(dependency)

    # No ownership from here on. You MUST keep a valid reference to dependency.
    # result.value will be initialized to NULL here, so it doesn't need to be done
    # anywhere else.
    cdef fast_get(self, PyObject *dependency, DependencyResult *result):
        cdef:
            CacheValue *value
            unsigned long clock
            PyObject *ptr

        result.value = NULL
        value = (<DependencyCache> self.__cache).get(dependency)
        if value:
            if value.header & HEADER_FLAG_SINGLETON:
                result.header = value.header
                result.value = value.ptr
                Py_XINCREF(result.value)
            else:
                self.__safe_cache_provide(dependency, result, value)
        else:
            clock = self.__singletons_clock
            ptr = PyDict_GetItem(<PyObject*> self._singletons, dependency)
            if ptr:
                result.header = HEADER_FLAG_SINGLETON
                result.value = ptr
                Py_XINCREF(result.value)
            else:
                self.__safe_provide(dependency, result, clock)

    cdef __safe_cache_provide(self,
                              PyObject *dependency,
                              DependencyResult *result,
                              CacheValue *cached):
        cdef:
            ScopeId scope_id
            PyObject *value
            object lock = self._instantiation_lock
            PyObject *stack = <PyObject*> self._dependency_stack
            PyObject *scope_dependencies = <PyObject*> self._scope_dependencies

        lock_fastrlock(lock, -1, True)

        if cached.header & HEADER_FLAG_HAS_SCOPE:
            scope_id = header_get_scope_id(cached.header)
            value = PyDict_GetItem(
                PyList_GET_ITEM(scope_dependencies, scope_id - 1),
                dependency
            )
            if value:
                unlock_fastrlock(lock)
                result.header = cached.header
                result.value = value
                Py_XINCREF(result.value)
                return

        if 0 != (<DependencyStack> stack).push(dependency):
            error = (<DependencyStack> stack).reset_with_error(dependency)
            unlock_fastrlock(lock)
            raise error

        try:
            (<RawProvider> cached.ptr).fast_provide(dependency, <PyObject*> self, result)
            assert result.value, "Once cached, a dependency must always be providable"
            cached.header = result.header
            if result.header & HEADER_FLAG_SINGLETON:
                PyDict_SetItem(<PyObject*> self._singletons, dependency, result.value)
                self.__singletons_clock += 1
                Py_XDECREF(cached.ptr)
                cached.ptr = result.value
                Py_XINCREF(result.value)
            elif result.header & HEADER_FLAG_HAS_SCOPE:
                scope_id = header_get_scope_id(result.header)
                PyDict_SetItem(
                    PyList_GET_ITEM(scope_dependencies, scope_id - 1),
                    dependency,
                    result.value
                )
        except Exception as error:
            new_error = handle_error(dependency, stack, error)
            if new_error is not error:
                raise new_error from error
            else:
                raise
        finally:
            (<DependencyStack> stack).pop()
            unlock_fastrlock(lock)

    cdef __safe_provide(self,
                        PyObject *dependency,
                        DependencyResult *result,
                        unsigned long singletons_clock):
        cdef:
            PyObject *value
            PyObject *provider
            ScopeId scope_id
            Exception error
            object lock = self._instantiation_lock
            PyObject *singletons = <PyObject*> self._singletons
            PyObject *stack = <PyObject*> self._dependency_stack
            PyObject *providers
            PyObject *scope_dependencies
            size_t i

        lock_fastrlock(lock, -1, True)

        # If anything changed in the singletons the clock would be different
        # otherwise no need to re-check the dictionary.
        if singletons_clock < self.__singletons_clock:
            value = PyDict_GetItem(singletons, dependency)
            if value:
                unlock_fastrlock(lock)
                result.header = HEADER_FLAG_SINGLETON
                result.value = value
                Py_XINCREF(result.value)
                return

        scope_dependencies = <PyObject*> self._scope_dependencies
        for i in range(<size_t> PyList_Size(scope_dependencies)):
            value = PyDict_GetItem(PyList_GET_ITEM(scope_dependencies, i), dependency)
            if value:
                unlock_fastrlock(lock)
                result.header = header_scope(i + 1)
                result.value = value
                Py_XINCREF(result.value)
                return

        if 0 != (<DependencyStack> stack).push(dependency):
            error = (<DependencyStack> stack).reset_with_error(dependency)
            unlock_fastrlock(lock)
            raise error

        try:
            providers = <PyObject*> self._providers
            for i in range(<size_t> PyList_Size(providers)):
                provider = PyList_GET_ITEM(providers, i)
                (<RawProvider> provider).fast_provide(
                    dependency,
                    <PyObject*> self,
                    result
                )
                if result.value:
                    if result.header & HEADER_FLAG_SINGLETON:
                        PyDict_SetItem(singletons, dependency, result.value)
                        self.__singletons_clock += 1
                        (<DependencyCache> self.__cache).set(dependency,
                                                             result.header,
                                                             result.value)
                    else:
                        if result.header & HEADER_FLAG_CACHEABLE:
                            (<DependencyCache> self.__cache).set(dependency,
                                                                 result.header,
                                                                 provider)
                        if result.header & HEADER_FLAG_HAS_SCOPE:
                            scope_id = header_get_scope_id(result.header)
                            PyDict_SetItem(
                                PyList_GET_ITEM(scope_dependencies, scope_id - 1),
                                dependency,
                                result.value
                            )
                    return

        except Exception as error:
            new_error = handle_error(dependency, stack, error)
            if new_error is not error:
                raise new_error from error
            else:
                raise
        finally:
            (<DependencyStack> stack).pop()
            unlock_fastrlock(lock)

cdef inline object handle_error(PyObject *dependency, PyObject *stack, object error):
    if isinstance(error, DependencyCycleError):
        return error

    if isinstance(error, DependencyInstantiationError):
        if (<DependencyStack> stack).depth == 1:
            return DependencyInstantiationError(<object> dependency)
        else:
            return error
    return DependencyInstantiationError(<object> dependency,
                                        (<DependencyStack> stack).to_list()[1:])

#########
# CACHE #
#########

cdef struct Entry:
    PyObject *key
    CacheValue value

cdef Entry*create_table(size_t size):
    cdef:
        Entry*table
        Entry*entry

    table = <Entry*> PyMem_Malloc(size * sizeof(Entry))
    if not table:
        raise MemoryError()

    for entry in table[:size]:
        entry.key = NULL

    return table

cdef class DependencyCache:
    cdef:
        size_t mask
        size_t used
        size_t singletons
        Entry *table

    def __cinit__(self):
        cdef:
            size_t size = 8
        self.table = create_table(size)
        self.mask = size - 1
        self.used = 0

    def __dealloc__(self):
        cdef:
            Entry *entry
        for entry in self.table[:self.mask + 1]:
            if entry.key:
                Py_XDECREF(entry.key)
                Py_XDECREF(entry.value.ptr)
        PyMem_Free(self.table)

    # Python functions only used for tests.
    def __len__(self):
        return self.used

    def __setitem__(self, key, value):
        self.set(<PyObject*> key, 0, <PyObject*> value)

    def __getitem__(self, key):
        cdef:
            CacheValue*value = self.get(<PyObject*> key)
        if value is NULL:
            raise KeyError(key)
        return <object> value.ptr

    cdef CacheValue*get(self, PyObject *key):
        """ The Container may update the CacheValue """
        cdef:
            Entry*entry = self._find(key)
        if entry.key:
            return &entry.value
        return NULL

    cdef set(self, PyObject *key, Header header, PyObject *value):
        cdef:
            Entry*entry = self._find(key)
        if entry.key is NULL:
            self.used += 1
            Py_XINCREF(key)
            Py_XINCREF(value)
            entry.key = key
            entry.value.header = header
            entry.value.ptr = value

            if 3 * self.used > 2 * self.mask:
                self._resize()
        else:
            Py_XINCREF(value)
            Py_XDECREF(entry.value.ptr)
            entry.value.header = header
            entry.value.ptr = value

    cdef _resize(self):
        cdef:
            Entry*old_table = self.table
            size_t old_mask = self.mask
            size_t size = 8
            size_t minsize = 2 * self.used

        while size < minsize:
            size *= 2

        # We don't need thread-safety thanks to the GIL. Whenever we use set(),
        # it's because the value didn't exist and we don't keep any dangling
        # cached value.
        self.table = create_table(size)
        self.mask = size - 1
        self.used = 0

        cdef:
            Entry*old_entry
            Entry*entry
            size_t i
        for old_entry in old_table[:old_mask + 1]:
            if old_entry.key:
                entry = self._find(old_entry.key)
                entry[0] = old_entry[0]
                self.used += 1

        PyMem_Free(old_table)

    cdef Entry*_find(self, PyObject *key):
        cdef:
            size_t mask = self.mask
            Entry*table = self.table
            Entry*cursor
            size_t i, perturb
            size_t h = (<size_t> key)

        # Python objects are at least 2 * size_t long.
        h //= 2 * sizeof(size_t)
        # Mixing the entropy into the lower bytes. Same strategy than scala's OpenHashMap.
        i = h ^ (h >> 20) ^ (h >> 12)
        i ^= (i >> 7) ^ (i >> 4)

        # Using same strategy than Python dict
        perturb = h
        while True:
            cursor = &(table[i & mask])
            if cursor.key is key or cursor.key is NULL:
                return cursor
            perturb >>= 5
            i = (5 * i + 1) + perturb

############
# OVERRIDE #
############

cdef class OverridableRawContainer(RawContainer):
    cdef:
        object __override_lock
        dict __scopes_override
        dict __singletons_override
        dict __factory_overrides
        object __provider_overrides


    def __init__(self):
        from collections import defaultdict
        super().__init__()
        self._is_clone = True
        self.__override_lock = threading.RLock()
        # Used to differentiate singletons from the overrides and the "normal" ones.
        self.__singletons_override = dict()
        self.__scopes_override = dict() # type:  Dict[Scope, Dict[Hashable, object]]
        self.__factory_overrides = dict()  # type: Dict[Any, Tuple[Callable[[], Any], Optional[Scope]]]
        self.__provider_overrides = deque()  # type: Deque[Callable[[Any], Optional[DependencyInstance]]]

    @classmethod
    def from_clone(cls, RawContainer cloned) -> 'OverridableRawContainer':
        cdef:
            OverridableRawContainer container = OverridableRawContainer()

        container._singletons = cloned._singletons
        container._scopes = cloned._scopes
        container._scope_dependencies = cloned._scope_dependencies
        for scope in container._scopes:
            container.__scopes_override[scope] = dict()
        container._providers = cloned._providers

        if isinstance(cloned, OverridableRawContainer):
            container.__singletons_override = (
                <OverridableRawContainer> cloned).__singletons_override
            container.__factory_overrides = (
                <OverridableRawContainer> cloned).__factory_overrides
            container.__provider_overrides = (
                <OverridableRawContainer> cloned).__provider_overrides
        return container

    def override_singletons(self, singletons: dict):
        with self.__override_lock:
            self.__singletons_override.update(singletons)

    def override_factory(self,
                         dependency: Hashable,
                         *,
                         factory: Callable[[], Any],
                         scope: Optional[Scope]):
        with self.__override_lock:
            self.__factory_overrides[dependency] = (factory, scope)

    def override_provider(self,
                          provider: Callable[[Any], Optional[DependencyInstance]]):
        with self.__override_lock:
            self.__provider_overrides.appendleft(provider)  # latest provider wins

    def reset_scope(self, scope: Scope) -> None:
        super().reset_scope(scope)
        self.__scopes_override[scope] = dict()

    def clone(self,
              *,
              keep_singletons: bool,
              keep_scopes: bool) -> 'OverridableRawContainer':
        cdef:
            OverridableRawContainer container

        with self.__override_lock:
            container = super().clone(keep_singletons=keep_singletons,
                                      keep_scopes=keep_scopes)
            if keep_singletons:
                container.__singletons_override = self.__singletons_override.copy()
            container.__scopes_override = {
                scope: dependencies.copy() if keep_scopes else dict()
                for scope, dependencies in self.__scopes_override.items()
            }
            container.__factory_overrides = self.__factory_overrides.copy()
            container.__provider_overrides = self.__provider_overrides.copy()

        return container

    def debug(self, dependency: Hashable):
        from .._internal.utils.debug import debug_repr
        from .utils import DependencyDebug

        with self.__override_lock:
            try:
                value = self.__singletons_override[dependency]
            except KeyError:
                pass
            else:
                return DependencyDebug(f"Override/Singleton: {debug_repr(dependency)} "
                                       f"-> {value!r}",
                                       scope=Scope.singleton())
            try:
                (factory, scope) = self.__factory_overrides[dependency]
            except KeyError:
                pass
            else:
                return DependencyDebug(f"Override/Factory: {debug_repr(dependency)} "
                                       f"-> {debug_repr(factory)}",
                                       scope=scope)

        return super().debug(dependency)

    # Less efficient than the original fast_get, but we don't really care in tests.
    cdef fast_get(self, PyObject *dependency, DependencyResult *result):
        cdef:
            PyObject *ptr

        dep = <object> dependency
        result.value = NULL
        with self.__override_lock, self._instantiation_lock:
            with self._dependency_stack.instantiating(dep):
                try:
                    obj = self.__singletons_override[dep]
                except KeyError:
                    pass
                else:
                    DependencyInstance(obj, scope=_SCOPE_SINGLETON).to_result(result)
                    return

                for scope, dependencies in self.__scopes_override.items():
                    try:
                        obj = dependencies[dep]
                    except KeyError:
                        pass
                    else:
                        DependencyInstance(obj, scope=scope).to_result(result)
                        return

                try:
                    for provider in self.__provider_overrides:
                        di = provider(dep)
                        if di is not None:
                            if di.scope is Scope.singleton():
                                self.__singletons_override[dep] = di.value
                            elif di.scope is not None:
                                self.__scopes_override[di.scope][dep] = di.value
                            (<DependencyInstance?> di).to_result(result)
                            return

                    try:
                        (factory, scope) = self.__factory_overrides[dep]
                    except KeyError:
                        pass
                    else:
                        value = factory()
                        if scope is Scope.singleton():
                            self.__singletons_override[dep] = value
                        elif scope is not None:
                            self.__scopes_override[scope][dep] = value
                        DependencyInstance(value, scope=scope).to_result(result)
                        return

                except Exception as error:
                    new_error = handle_error(dependency,
                                             <PyObject*> self._dependency_stack,
                                             error)
                    if new_error is not error:
                        raise new_error from error
                    else:
                        raise

            RawContainer.fast_get(self, dependency, result)
