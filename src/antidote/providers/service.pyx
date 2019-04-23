# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
import inspect
from typing import Any, Callable, Dict, Tuple, Optional, Union

# @formatter:off
from cpython.dict cimport PyDict_GetItem
from cpython.ref cimport PyObject

from antidote.core.container cimport (DependencyContainer, DependencyInstance,
                                     DependencyProvider)
from ..exceptions import DuplicateDependencyError, DependencyNotFoundError
# @formatter:on


cdef class LazyFactory:
    def __init__(self, dependency):
        self.dependency = dependency


cdef class Build:
    def __init__(self, *args, **kwargs):
        if not args:
            raise TypeError("At least the dependency and one additional argument "
                            "are mandatory.")

        self.wrapped = args[0]
        self.args = args[1:]  # type: Tuple
        self.kwargs = kwargs  # type: Dict

        if not self.args and not self.kwargs:
            raise TypeError("Without additional arguments, Build must not be used.")

    def __repr__(self):
        return "{}(id={!r}, args={!r}, kwargs={!r})".format(type(self).__name__,
                                                            self.wrapped,
                                                            self.args,
                                                            self.kwargs)

    __str__ = __repr__

    def __hash__(self):
        try:
            # Try most precise hash first
            return hash((self.wrapped, self.args, tuple(self.kwargs.items())))
        except TypeError:
            # If type error, return the best error-free hash possible
            return hash((self.wrapped, len(self.args), tuple(self.kwargs.keys())))

    def __eq__(self, object other):
        return isinstance(other, Build) \
               and (self.wrapped is other.wrapped or self.wrapped == other.wrapped) \
               and self.args == other.args \
               and self.kwargs == self.kwargs

cdef class ServiceProvider(DependencyProvider):
    bound_dependency_types = (Build,)

    def __init__(self, DependencyContainer container):
        super().__init__(container)
        self._service_to_factory = dict()  # type: Dict[Any, ServiceFactory]

    def __repr__(self):
        return "{}(factories={!r})".format(type(self).__name__,
                                           tuple(self._service_to_factory.keys()))

    cpdef DependencyInstance provide(self, object dependency):
        cdef:
            ServiceFactory factory
            Build build
            PyObject*ptr
            object instance
            object dependency_instance

        if isinstance(dependency, Build):
            build = <Build> dependency
            ptr = PyDict_GetItem(self._service_to_factory, build.wrapped)
            if ptr != NULL:
                factory = <ServiceFactory> ptr

                if factory.lazy_dependency is not None:
                    dependency_instance = self._container.provide(factory.lazy_dependency)
                    if dependency_instance is None:
                        raise DependencyNotFoundError(dependency_instance)
                    factory.lazy_dependency = None
                    factory.func = dependency_instance

                if factory.takes_dependency:
                    instance = factory.func(build.wrapped, *build.args, **build.kwargs)
                else:
                    instance = factory.func(*build.args, **build.kwargs)
            else:
                return
        else:
            ptr = PyDict_GetItem(self._service_to_factory, dependency)
            if ptr != NULL:
                factory = <ServiceFactory> ptr

                if factory.lazy_dependency is not None:
                    dependency_instance = self._container.provide(factory.lazy_dependency)
                    if dependency_instance is None:
                        raise DependencyNotFoundError(dependency_instance)
                    factory.lazy_dependency = None
                    factory.func = dependency_instance

                if factory.takes_dependency:
                    instance = factory.func(dependency)
                else:
                    instance = factory.func()
            else:
                return

        return DependencyInstance.__new__(DependencyInstance,
                                          instance,
                                          factory.singleton)

    def register(self,
                 service,
                 factory: Union[Callable, LazyFactory] = None,
                 bint singleton: bool = True,
                 bint takes_dependency: bool = False):
        if not inspect.isclass(service):
            raise TypeError("A service must be a class, not a {!r}".format(service))

        if isinstance(factory, LazyFactory):
            service_factory = ServiceFactory(
                singleton=singleton,
                func=None,
                lazy_dependency=factory.dependency,
                takes_dependency=takes_dependency
            )
        elif factory is None or callable(factory):
            service_factory = ServiceFactory(
                singleton=singleton,
                func=service if factory is None else factory,
                lazy_dependency=None,
                takes_dependency=takes_dependency
            )
        else:
            raise TypeError("factory must be callable or be a Lazy dependency.")

        if service in self._service_to_factory:
            raise DuplicateDependencyError(service)

        self._service_to_factory[service] = service_factory


cdef class ServiceFactory:
    cdef:
        readonly object func
        readonly bint singleton
        readonly bint takes_dependency
        readonly object lazy_dependency

    def __init__(self,
                 bint singleton,
                 func: Optional[Callable],
                 lazy_dependency: Optional[Any],
                 bint takes_dependency):
        assert func is not None or lazy_dependency is not None
        self.singleton = singleton
        self.func = func
        self.lazy_dependency = lazy_dependency
        self.takes_dependency = takes_dependency

    def __repr__(self):
        return "{}(func={!r}, singleton={!r}, takes_dependency={!r}," \
               "lazy_dependency={!r})".format(
            type(self).__name__,
            self.func,
            self.singleton,
            self.takes_dependency,
            self.lazy_dependency,
        )
