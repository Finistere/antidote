# cython: language_level=3
# cython: boundscheck=False, wraparound=False
import inspect
from typing import Any, Callable, Dict, Optional, Tuple, Union

# @formatter:off
from cpython.dict cimport PyDict_GetItem
from cpython.ref cimport PyObject

from antidote.core.container cimport (DependencyContainer, DependencyInstance,
                                     DependencyProvider)
from ..exceptions import DuplicateDependencyError
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
        return (f"{type(self).__name__}(id={self.wrapped!r}, "
                f"args={self.args!r}, kwargs={self.kwargs!r})")

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
        return (f"{type(self).__name__}("
                f"factories={tuple(self._service_to_factory.keys())!r})")

    cpdef DependencyInstance provide(self, object dependency):
        cdef:
            ServiceFactory factory
            Build build
            PyObject*ptr
            DependencyInstance dependency_instance
            object instance

        ptr = PyDict_GetItem(self._service_to_factory, dependency)
        if ptr != NULL:
            factory = <ServiceFactory> ptr
            if factory.lazy_dependency is not None:
                factory.func = self._container.get(factory.lazy_dependency)
                factory.lazy_dependency = None

            if factory.takes_dependency:
                instance = factory.func(dependency)
            else:
                instance = factory.func()

            return DependencyInstance.__new__(DependencyInstance,
                                              instance,
                                              factory.singleton)
        elif isinstance(dependency, Build):
            build = <Build> dependency
            ptr = PyDict_GetItem(self._service_to_factory, build.wrapped)

            if ptr != NULL:
                factory = <ServiceFactory> ptr
                if factory.lazy_dependency is not None:
                    factory.func = self._container.get(factory.lazy_dependency)
                    factory.lazy_dependency = None

                if factory.takes_dependency:
                    instance = factory.func(build.wrapped, *build.args, **build.kwargs)
                else:
                    instance = factory.func(*build.args, **build.kwargs)

            return DependencyInstance.__new__(DependencyInstance,
                                              instance,
                                              factory.singleton)

        return None

    def register(self,
                 service,
                 factory: Union[Callable, LazyFactory] = None,
                 bint singleton: bool = True,
                 bint takes_dependency: bool = False):
        if not inspect.isclass(service):
            raise TypeError(f"A service must be a class, not a {service!r}")

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
            raise DuplicateDependencyError(service, self._service_to_factory[service])

        self._service_to_factory[service] = service_factory

        return service

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
        return (f"{type(self).__name__}(func={self.func!r}, "
                f"singleton={self.singleton!r}, "
                f"takes_dependency={self.takes_dependency!r}, "
                f"lazy_dependency={self.lazy_dependency!r})")
