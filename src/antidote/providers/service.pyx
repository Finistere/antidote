from typing import Callable, Dict, Hashable

# @formatter:off
cimport cython
from cpython.object cimport PyObject_Call, PyObject_CallObject
from cpython.ref cimport PyObject
from cpython.tuple cimport PyTuple_Pack

from antidote.core.container cimport (DependencyResult, FastDependencyProvider,
                                      FLAG_DEFINED, FLAG_SINGLETON, PyObjectBox,
                                      RawDependencyContainer)
from ..exceptions import DependencyNotFoundError, DuplicateDependencyError
# @formatter:on

cdef extern from "Python.h":
    int PyObject_IsInstance(PyObject *inst, PyObject *cls) except -1
    PyObject*PyDict_GetItem(PyObject *p, PyObject *key)


@cython.final
cdef class Build:
    def __init__(self, dependency: Hashable, kwargs: Dict):
        assert isinstance(kwargs, dict) and len(kwargs) > 0
        self.dependency = dependency  # type: Hashable
        self.kwargs = kwargs  # type: Dict

        try:
            # Try most precise hash first
            self._hash = hash((self.dependency, tuple(self.kwargs.items())))
        except TypeError:
            # If type error, return the best error-free hash possible
            self._hash = hash((self.dependency, tuple(self.kwargs.keys())))

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return f"{type(self).__name__}(dependency={self.dependency}, kwargs={self.kwargs})"

    def __eq__(self, other):
        return isinstance(other, Build) \
               and (self.dependency is other.dependency
                    or self.dependency == other.dependency) \
               and self.kwargs == other.kwargs

@cython.final
cdef class ServiceProvider(FastDependencyProvider):
    """
    Provider managing factories. Also used to register classes directly.
    """
    cdef:
        dict __services
        tuple __empty_tuple
        bint __frozen
        object __freeze_lock

    def __init__(self):
        super().__init__()
        self.__empty_tuple = tuple()
        super().__init__()
        self.__services = dict()  # type: Dict[Hashable, Service]

    def __repr__(self):
        return f"{type(self).__name__}(factories={tuple(self.__services.keys())!r})"

    def clone(self) -> Service:
        p = ServiceProvider()
        p.__services = {k: v.copy() for k, v in self.__services.items()}
        return p

    cdef fast_provide(self,
                      PyObject*dependency,
                      PyObject*container,
                      DependencyResult*result):
        cdef:
            PyObject*service
            tuple args
            object factory
            bint is_build_dependency = PyObject_IsInstance(dependency, <PyObject*> Build)

        if is_build_dependency:
            service = PyDict_GetItem(<PyObject*> self.__services,
                                     <PyObject*> (<Build> dependency).dependency)
        else:
            service = PyDict_GetItem(<PyObject*> self.__services, dependency)

        if service == NULL:
            return

        if (<Service> service).factory_dependency is not None:
            (<RawDependencyContainer> container).fast_get(
                <PyObject*> (<Service> service).factory_dependency, result)
            if result.flags == 0:
                raise DependencyNotFoundError(<object> dependency)
            elif (result.flags & FLAG_SINGLETON) != 0:
                (<Service> service).factory_dependency = None
                (<Service> service).factory = (<PyObjectBox> result.box).obj
            factory = (<PyObjectBox> result.box).obj
        else:
            factory = (<Service> service).factory

        result.flags = FLAG_DEFINED | (<Service> service).flags
        if is_build_dependency:
            if (<Service> service).takes_dependency:
                args = PyTuple_Pack(1, <PyObject*> (<Build> dependency).dependency)
                (<PyObjectBox> result.box).obj = PyObject_Call(
                    factory,
                    args,
                    (<Build> dependency).kwargs
                )
            else:
                (<PyObjectBox> result.box).obj = PyObject_Call(
                    factory,
                    self.__empty_tuple,
                    (<Build> dependency).kwargs
                )
        else:
            if (<Service> service).takes_dependency:
                args = PyTuple_Pack(1, <PyObject*> dependency)
                (<PyObjectBox> result.box).obj = PyObject_CallObject(factory, args)
            else:
                (<PyObjectBox> result.box).obj = PyObject_CallObject(factory,
                                                                     <object> NULL)

    def register(self, class_: type, singleton: bool = True):
        """
        Register a class which is both dependency and factory.

        Args:
            class_: dependency to register.
            singleton: Whether the dependency should be mark as singleton or
                not for the :py:class:`~..core.DependencyContainer`.
        """
        with self._ensure_not_frozen():
            self.register_with_factory(dependency=class_, factory=class_,
                                       singleton=singleton, takes_dependency=False)
        return class_

    def register_with_factory(self,
                              dependency: Hashable,
                              factory: Callable,
                              singleton: bool = True,
                              takes_dependency: bool = False):
        """
        Registers a factory for a dependency.

        Args:
            dependency: dependency to register.
            factory: Callable used to instantiate the dependency.
            singleton: Whether the dependency should be mark as singleton or
                not for the :py:class:`~..core.DependencyContainer`.
            takes_dependency: If True, the factory will be given the requested
                dependency as its first arguments. This allows re-using the
                same factory for different dependencies.
        """
        with self._ensure_not_frozen():
            if dependency in self.__services:
                raise DuplicateDependencyError(dependency,
                                               self.__services[dependency])

            if callable(factory):
                self.__services[dependency] = Service(singleton=singleton,
                                                      takes_dependency=takes_dependency,
                                                      factory=factory)
            else:
                raise TypeError(f"factory must be callable, not {type(factory)!r}.")

    def register_with_providable_factory(self,
                                         dependency: Hashable,
                                         factory_dependency: Hashable,
                                         singleton: bool = True,
                                         takes_dependency: bool = False):
        """
        Registers a lazy factory (retrieved only at the first instantiation) for
        a dependency.

        Args:
            dependency: dependency to register.
            factory_dependency: Dependency used to retrieve.
            singleton: Whether the dependency should be mark as singleton or
                not for the :py:class:`~..core.DependencyContainer`.
            takes_dependency: If True, the factory will be given the requested
                dependency as its first arguments. This allows re-using the
                same factory for different dependencies.
        """
        with self._ensure_not_frozen():
            if dependency in self.__services:
                raise DuplicateDependencyError(dependency,
                                               self.__services[dependency])

            self.__services[dependency] = Service(singleton=singleton,
                                                  takes_dependency=takes_dependency,
                                                  factory_dependency=factory_dependency)

@cython.final
cdef class Service:
    """
    Not part of the public API.

    Only used by the FactoryProvider to store information on how the factory
    has to be used.
    """
    cdef:
        size_t flags
        bint takes_dependency
        object factory
        object factory_dependency

    def __init__(self,
                 bint singleton,
                 bint takes_dependency,
                 factory: Callable = None,
                 factory_dependency: Hashable = None):
        assert factory is not None or factory_dependency is not None
        self.flags = FLAG_SINGLETON if singleton else 0
        self.takes_dependency = takes_dependency
        self.factory = factory
        self.factory_dependency = factory_dependency

    def __repr__(self):
        return (f"{type(self).__name__}(singleton={self.flags == FLAG_SINGLETON}, "
                f"takes_dependency={self.takes_dependency}, factory={self.factory}, "
                f"factory_dependency={self.factory_dependency})")

    def copy(self):
        return Service(self.flags == FLAG_SINGLETON,
                       self.takes_dependency,
                       self.factory,
                       self.factory_dependency)
