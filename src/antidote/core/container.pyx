# cython: language_level=3
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
        return (f"DependencyInstance(instance={self.instance!r}, "
                f"singleton={self.singleton!r})")

cdef class DependencyContainer:
    def __init__(self):
        self._providers = list()  # type: List[DependencyProvider]
        self._type_to_provider = dict()  # type: Dict[type, DependencyProvider]
        self._singletons = dict()  # type: Dict[Any, DependencyInstance]
        self._singletons[DependencyContainer] = DependencyInstance(self, True)
        self._dependency_stack = DependencyStack()
        self._instantiation_lock = create_fastrlock()

    def __str__(self):
        return (f"{type(self).__name__}(providers={self._providers}, "
                f"type_to_provider={self._type_to_provider})")

    def __repr__(self):
        return (f"{type(self).__name__}(providers={self._providers!r}, "
                f"type_to_provider={self._type_to_provider!r}, "
                f"singletons={self._singletons!r})")

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
                raise RuntimeError(f"Cannot bind {bound_type!r} to provider, "
                                   f"already bound to "
                                   f"{self._type_to_provider[bound_type]!r}")

        for bound_type in provider.bound_dependency_types:
            self._type_to_provider[bound_type] = provider

        self._providers.append(provider)

    def update_singletons(self, dependencies: Mapping):
        """
        Update the singletons.
        """
        lock_fastrlock(self._instantiation_lock, -1, True)
        self._singletons.update({
            k: DependencyInstance(v, singleton=True)
            for k, v in dependencies.items()
        })
        unlock_fastrlock(self._instantiation_lock)

    cpdef object get(self, dependency):
        return self.safe_provide(dependency).instance

    cpdef DependencyInstance safe_provide(self, object dependency):
        cdef:
            DependencyInstance dependency_instance

        dependency_instance = self.provide(dependency)
        if dependency_instance is None:
            raise DependencyNotFoundError(dependency)
        return dependency_instance

    cpdef DependencyInstance provide(self, object dependency):
        cdef:
            DependencyInstance dependency_instance = None
            DependencyProvider provider
            PyObject*ptr
            Exception e
            list stack

        ptr = PyDict_GetItem(self._singletons, dependency)
        if ptr != NULL:
            return <DependencyInstance> ptr

        lock_fastrlock(self._instantiation_lock, -1, True)

        ptr = PyDict_GetItem(self._singletons, dependency)
        if ptr != NULL:
            unlock_fastrlock(self._instantiation_lock)
            return <DependencyInstance> ptr

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
                    PyDict_SetItem(self._singletons, dependency, dependency_instance)
                return dependency_instance

        except Exception as e:
            if isinstance(e, DependencyCycleError):
                raise
            raise DependencyInstantiationError(dependency) from e
        finally:
            self._dependency_stack.pop()
            unlock_fastrlock(self._instantiation_lock)

        return None

cdef class DependencyProvider:
    bound_dependency_types = ()  # type: Tuple[type]

    def __init__(self, DependencyContainer container):
        self._container = container

    cpdef DependencyInstance provide(self, dependency):
        raise NotImplementedError()
