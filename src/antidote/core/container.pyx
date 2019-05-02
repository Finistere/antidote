# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False
from typing import (Any, Dict, Hashable, List, Mapping, Tuple)

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
    """
    Simple wrapper used by a :py:class:`~.core.DependencyProvider` when returning
    an instance of a dependency so it can specify in which scope the instance
    belongs to.
    """
    def __cinit__(self, object instance, bint singleton = False):
        self.instance = instance
        self.singleton = singleton

    def __repr__(self):
        return "{}(instance={!r}, singleton={!r})".format(type(self).__name__,
                                                          self.instance,
                                                          self.singleton)

cdef class DependencyContainer:
    """
    Instantiates the dependencies through the registered providers and handles
    their scope.
    """

    def __init__(self):
        self._providers = list()  # type: List[DependencyProvider]
        self._type_to_provider = dict()  # type: Dict[type, DependencyProvider]
        self._singletons = dict()  # type: Dict[Any, DependencyInstance]
        self._singletons[DependencyContainer] = DependencyInstance(self, True)
        self._dependency_stack = DependencyStack()
        self._instantiation_lock = create_fastrlock()

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
        """ Returns a mapping of all the registered providers by their type. """
        return {type(p): p for p in self._providers}

    @property
    def singletons(self):
        """ Returns all the defined singletons """
        return self._singletons.copy()

    def register_provider(self, provider: Hashable):
        """
        Registers a provider, which can then be used to instantiate dependencies.

        Args:
            provider: Provider instance to be registered.

        """
        if not isinstance(provider, DependencyProvider):
            raise TypeError("provider must be a DependencyProvider, not a {!r}".format(
                type(provider)
            ))

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
        self._singletons.update({
            k: DependencyInstance(v, singleton=True)
            for k, v in dependencies.items()
        })
        unlock_fastrlock(self._instantiation_lock)

    cpdef object get(self, object dependency: Hashable):
        """
        Returns an instance for the given dependency. All registered providers
        are called sequentially until one returns an instance.  If none is
        found, :py:exc:`~.exceptions.DependencyNotFoundError` is raised.

        Args:
            dependency: Passed on to the registered providers.

        Returns:
            instance for the given dependency
        """
        return self.safe_provide(dependency).instance

    cpdef DependencyInstance safe_provide(self, object dependency):
        cdef:
            DependencyInstance dependency_instance

        dependency_instance = self.provide(dependency)
        if dependency_instance is None:
            raise DependencyNotFoundError(dependency)
        return dependency_instance

    cpdef DependencyInstance provide(self, object dependency: Hashable):
        """
        Internal method which should not be directly called. Prefer
        :py:meth:`~.core.core.DependencyContainer.get`.
        It may be overridden in a subclass to customize how dependencies are
        instantiated.

        Used by the injection wrappers.
        """
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
    """
    Abstract base class for a Provider.

    Used by the :py:class:`~.core.DependencyContainer` to instantiate
    dependencies. Several are used in a cooperative manner : the first instance
    to be returned by one of them is used. Thus providers should ideally not
    overlap and handle only one kind of dependencies such as strings or tag.

    This should be used whenever one needs to introduce a new kind of dependency,
    or control how certain dependencies are instantiated.
    """
    bound_dependency_types = ()  # type: Tuple[type]

    def __init__(self, DependencyContainer container):
        self._container = container

    cpdef DependencyInstance provide(self, dependency: Hashable):
        """
        Method called by the :py:class:`~.core.DependencyContainer` when
        searching for a dependency.

        It is necessary to check quickly if the dependency can be provided or
        not, as :py:class:`~.core.DependencyContainer` will try its
        registered providers. A good practice is to subclass
        :py:class:`~.core.Dependency` so custom dependencies be differentiated.

        Args:
            dependency: The dependency to be provided by the provider.

        Returns:
            The requested instance wrapped in a :py:class:`~.core.Instance`
            if available or :py:obj:`None`.
        """
        raise NotImplementedError()
