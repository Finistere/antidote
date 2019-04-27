# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False, annotation_typing=False
from typing import Any, Dict, List, Mapping, Tuple

# @formatter:off
cimport cython
from cpython.dict cimport PyDict_GetItem, PyDict_SetItem
from cpython.ref cimport PyObject
from fastrlock.rlock cimport create_fastrlock, lock_fastrlock, unlock_fastrlock

from antidote._internal.stack cimport DependencyStack
# @formatter:on
from ..exceptions import (DependencyCycleError, DependencyInstantiationError,
                          DependencyNotFoundError)


@cython.freelist(32)
cdef class DependencyInstance:
    def __cinit__(self, object instance, bint singleton = False):
        self.instance = instance
        self.singleton = singleton

    def __repr__(self):
        return "{}(item={!r}, singleton={!r})".format(type(self).__name__,
                                                      self.instance,
                                                      self.singleton)

cdef class DependencyContainer:
    def __init__(self):
        self._providers = list()  # type: List[DependencyProvider]
        self._type_to_provider = dict()  # type: Dict[type, DependencyProvider]
        self._singletons = dict()  # type: Dict[Any, Any]
        self._singletons[DependencyContainer] = self
        self._dependency_stack = DependencyStack()
        self._instantiation_lock = create_fastrlock()
        # class attributes do not exist in Cython
        self.SENTINEL = object()

    def __str__(self):
        return "{}(providers={!r}, type_to_provider={!r})".format(
            type(self).__name__,
            self._providers,
            self._type_to_provider
        )

    def __repr__(self):
        return "{}(providers={!r}, type_to_provider={!r}, singletons={!r})".format(
            type(self).__name__,
            self._providers,
            self._type_to_provider,
            self._singletons
        )

    @property
    def providers(self):
        return {type(p): p for p in self._providers}

    @property
    def singletons(self):
        return self._singletons.copy()

    def register_provider(self, provider):
        if not isinstance(provider, DependencyProvider):
            raise ValueError("Not a provider")

        for bound_type in provider.bound_dependency_types:
            if bound_type in self._type_to_provider:
                raise RuntimeError(
                    "Cannot bind {!r} to provider, already bound to {!r}".format(
                        bound_type, self._type_to_provider[bound_type]
                    )
                )

        for bound_type in provider.bound_dependency_types:
            self._type_to_provider[bound_type] = provider

        self._providers.append(provider)

    def update_singletons(self, dependencies: Mapping):
        """
        Update the singletons.
        """
        lock_fastrlock(self._instantiation_lock, -1, True)
        self._singletons.update(dependencies)
        unlock_fastrlock(self._instantiation_lock)

    def get(self, dependency):
        instance = self.provide(dependency)
        if instance is self.SENTINEL:
            raise DependencyNotFoundError(dependency)
        return instance

    cpdef object provide(self, object dependency):
        cdef:
            DependencyInstance dependency_instance = None
            DependencyProvider provider
            PyObject*ptr
            Exception e
            list stack

        ptr = PyDict_GetItem(self._singletons, dependency)
        if ptr != NULL:
            return <object> ptr

        lock_fastrlock(self._instantiation_lock, -1, True)

        ptr = PyDict_GetItem(self._singletons, dependency)
        if ptr != NULL:
            unlock_fastrlock(self._instantiation_lock)
            return <object> ptr

        if 1 != self._dependency_stack.push(dependency):
            stack = self._dependency_stack._stack.copy()
            unlock_fastrlock(self._instantiation_lock)
            stack.append(dependency)
            raise DependencyCycleError(stack)

        try:
            ptr = PyDict_GetItem(self._type_to_provider, type(dependency))
            if ptr != NULL:
                dependency_instance = (<DependencyProvider> ptr).provide(dependency)
            else:
                for provider in self._providers:
                    dependency_instance = provider.provide(dependency)
                    if dependency_instance is not None:
                        break

            if dependency_instance is not None:
                if dependency_instance.singleton:
                    PyDict_SetItem(self._singletons,
                                   dependency,
                                   dependency_instance.instance)
                return dependency_instance.instance

        except Exception as e:
            if isinstance(e, DependencyCycleError):
                raise
            raise DependencyInstantiationError(dependency) from e
        finally:
            self._dependency_stack.pop()
            unlock_fastrlock(self._instantiation_lock)

        return self.SENTINEL

cdef class DependencyProvider:
    bound_dependency_types = ()  # type: Tuple[type]

    def __init__(self, DependencyContainer container):
        self._container = container

    cpdef DependencyInstance provide(self, dependency):
        raise NotImplementedError()
