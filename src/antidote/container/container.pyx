# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False, annotation_typing=False
import threading
from typing import List

# @formatter:off
cimport cython
from cpython.dict cimport PyDict_GetItem, PyDict_SetItem
from cpython.object cimport PyObject_IsInstance
from cpython.ref cimport PyObject

# noinspection PyUnresolvedReferences
from .stack cimport InstantiationStack
# @formatter:on
from ..exceptions import (DependencyCycleError, DependencyInstantiationError,
                          DependencyNotFoundError)

cdef class DependencyContainer:
    def __init__(self):
        self._providers = list()  # type: List[Provider]
        self._singletons = dict()
        self._instantiation_lock = threading.RLock()
        self._instantiation_stack = InstantiationStack()
        # class attributes do not exist in Cython
        self.SENTINEL = object()

    @property
    def providers(self):
        return {type(p): p for p in self._providers}

    @property
    def singletons(self):
        return self._singletons.copy()

    def register_provider(self, provider):
        if not isinstance(provider, Provider):
            raise ValueError("Not a provider")

        self._providers.append(provider)

    def __str__(self):
        return "{}(providers=({}))".format(
            type(self).__name__,
            ", ".join("{}={}".format(name, p)
                      for name, p in self.providers.items()),
        )

    def __repr__(self):
        return "{}(providers=({}), singletons={!r})".format(
            type(self).__name__,
            ", ".join("{!r}={!r}".format(name, p)
                      for name, p in self.providers.items()),
            self._singletons
        )

    def __setitem__(self, dependency_id, dependency):
        with self._instantiation_lock:
            self._singletons[dependency_id] = dependency

    def __delitem__(self, dependency_id):
        with self._instantiation_lock:
            del self._singletons[dependency_id]

    def update(self, *args, **kwargs):
        with self._instantiation_lock:
            self._singletons.update(*args, **kwargs)

    def __getitem__(self, dependency_id):
        instance = self.provide(dependency_id)
        if instance is self.SENTINEL:
            raise DependencyNotFoundError(dependency_id)
        return instance

    cpdef object provide(self, object dependency_id):
        """
        Low level API for the injection wrapper.
        """
        cdef:
            Instance instance
            Provider provider
            Dependency dependency
            PyObject*ptr
            Exception e
            list stack

        ptr = PyDict_GetItem(self._singletons, dependency_id)
        if ptr != NULL:
            return <object> ptr

        self._instantiation_lock.acquire()
        if 1 != self._instantiation_stack.push(dependency_id):
            stack = self._instantiation_stack._stack.copy()
            stack.append(dependency_id)
            raise DependencyCycleError(stack)

        try:
            ptr = PyDict_GetItem(self._singletons, dependency_id)
            if ptr != NULL:
                return <object> ptr

            if 1 == PyObject_IsInstance(dependency_id, Dependency):
                dependency = dependency_id
            else:
                dependency = Dependency.__new__(Dependency)
                dependency.id = dependency_id

            for provider in self._providers:
                instance = provider.provide(dependency)
                if instance is not None:
                    if instance.singleton:
                        PyDict_SetItem(self._singletons, dependency_id, instance.item)
                    return instance.item
        except Exception as e:
            if isinstance(e, DependencyCycleError):
                raise
            raise DependencyInstantiationError(dependency_id) from e
        finally:
            self._instantiation_stack.pop()
            self._instantiation_lock.release()

        return self.SENTINEL

@cython.freelist(10)
cdef class Dependency:
    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return "{}(id={!r})".format(type(self).__name__, self.id)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, object other):
        return (self.id == other
                or (isinstance(other, Dependency) and self.id == other.id))

@cython.freelist(10)
cdef class Instance:
    def __init__(self, item, singleton: bool = False):
        self.item = item
        self.singleton = singleton

    def __repr__(self):
        return "{}(item={!r}, singleton={!r})".format(type(self).__name__, self.item,
                                                      self.singleton)

cdef class Provider:
    cpdef Instance provide(self, Dependency dependency):
        raise NotImplementedError()
