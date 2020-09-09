# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False
import threading
from typing import Any, Callable, Dict, Hashable, Optional

# @formatter:off
from cpython.ref cimport PyObject
from cpython.tuple cimport PyTuple_Pack
from cpython.object cimport PyObject_Call, PyObject_CallObject

from antidote.core.container cimport (DependencyContainer, FastDependencyProvider,
                                      DependencyResult, PyObjectBox, FLAG_DEFINED,
                                      FLAG_SINGLETON)
from ..core.exceptions import DependencyNotFoundError, FrozenWorldError
from ..exceptions import DuplicateDependencyError

# @formatter:on

cdef extern from "Python.h":
    int PyObject_IsInstance(PyObject *inst, PyObject *cls) except -1
    PyObject* PyDict_GetItem(PyObject *p, PyObject *key)

cdef class Build:
    """
    Custom Dependency wrapper used to pass arguments to the factory used to
    create the actual dependency.

    .. doctest::

        >>> from antidote import Build, register, world
        >>> @register
        ... class Dummy:
        ...     def __init__(self, name=None):
        ...         self.name = name
        >>> dummy = world.get(Build(Dummy, name='me'))
        >>> dummy.name
        'me'

    With no arguments, that is to say :code:`Build(x)`, it is equivalent to
    :code:`x` for the :py:class:`~.core.DependencyContainer`.
    """
    cdef:
        readonly object dependency
        readonly dict kwargs
        int _hash

    def __init__(self, dependency: Hashable, **kwargs):
        """
        Args:
            *args: The first argument is the dependency, all others are passed
                on to the factory.
            **kwargs: Passed on to the factory.
        """
        self.dependency = dependency  # type: Hashable
        self.kwargs = kwargs  # type: Dict

        if not self.kwargs:
            raise TypeError("Without additional arguments, Build must not be used.")

        try:
            # Try most precise hash first
            self._hash = hash((self.dependency, tuple(self.kwargs.items())))
        except TypeError:
            # If type error, return the best error-free hash possible
            self._hash = hash((self.dependency, tuple(self.kwargs.keys())))

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return "{}(id={!r}, kwargs={!r})".format(type(self).__name__,
                                                 self.dependency,
                                                 self.kwargs)

    __str__ = __repr__

    def __eq__(self, other):
        return isinstance(other, Build) \
               and (self.dependency is other.dependency
                    or self.dependency == other.dependency) \
               and self.kwargs == self.kwargs  # noqa

cdef class FactoryProvider(FastDependencyProvider):
    """
    Provider managing factories. Also used to register classes directly.
    """
    cdef:
        dict __builders
        tuple __empty_tuple
        bint __frozen
        object __freeze_lock

    def __init__(self):
        self.__builders = dict()  # type: Dict[Any, Builder]
        self.__empty_tuple = tuple()
        self.__freeze_lock = threading.RLock()
        self.__frozen = False

    def __repr__(self):
        return "{}(factories={!r})".format(type(self).__name__,
                                           tuple(self.__builders.keys()))

    def freeze(self):
        with self.__freeze_lock:
            self.__frozen = True

    def clone(self):
        p = FactoryProvider()
        p.__builders = self.__builders.copy()
        return p

    cdef fast_provide(self,
                      PyObject* dependency,
                      PyObject* container,
                      DependencyResult* result):
        cdef:
            PyObject*builder
            tuple args
            object factory
            bint is_build_dependency = PyObject_IsInstance(dependency, <PyObject*> Build)

        if is_build_dependency:
            builder = PyDict_GetItem(<PyObject*> self.__builders, <PyObject*> (<Build> dependency).dependency)
        else:
            builder = PyDict_GetItem(<PyObject*> self.__builders, dependency)

        if builder == NULL:
            return

        if (<Builder> builder).factory_dependency is not None:
            (<DependencyContainer> container).fast_get(<PyObject*> (<Builder> builder).factory_dependency, result)
            if result.flags == 0:
                raise DependencyNotFoundError(<object> dependency)
            elif (result.flags & FLAG_SINGLETON) != 0:
                (<Builder> builder).factory_dependency = None
                (<Builder> builder).factory = (<PyObjectBox> result.box).obj
            factory = (<PyObjectBox> result.box).obj
        else:
            factory = (<Builder> builder).factory

        result.flags = FLAG_DEFINED | (<Builder> builder).flags
        if is_build_dependency:
            if (<Builder> builder).takes_dependency:
                args = PyTuple_Pack(1, <PyObject*> (<Build> dependency).dependency)
                (<PyObjectBox> result.box).obj = PyObject_Call(factory, args, (<Build> dependency).kwargs)
            else:
                (<PyObjectBox> result.box).obj = PyObject_Call(factory, self.__empty_tuple, (<Build> dependency).kwargs)
        else:
            if (<Builder> builder).takes_dependency:
                args = PyTuple_Pack(1, <PyObject*> dependency)
                (<PyObjectBox> result.box).obj = PyObject_CallObject(factory, args)
            else:
                (<PyObjectBox> result.box).obj = PyObject_CallObject(factory, <object> NULL)

    def register_class(self, class_: type, singleton: bool = True):
        """
        Register a class which is both dependency and factory.

        Args:
            class_: dependency to register.
            singleton: Whether the dependency should be mark as singleton or
                not for the :py:class:`~..core.DependencyContainer`.
        """
        with self.__freeze_lock:
            if self.__frozen:
                raise FrozenWorldError(f"Cannot add {class_} to a frozen world.")
            self.register_factory(dependency=class_, factory=class_,
                                  singleton=singleton, takes_dependency=False)
        return class_

    def register_factory(self,
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
        if dependency in self.__builders:
            raise DuplicateDependencyError(dependency,
                                           self.__builders[dependency])

        if callable(factory):
            with self.__freeze_lock:
                if self.__frozen:
                    raise FrozenWorldError(f"Cannot add {dependency} to a frozen world.")
                self.__builders[dependency] = Builder(singleton=singleton,
                                                      takes_dependency=takes_dependency,
                                                      factory=factory)
        else:
            raise TypeError(f"factory must be callable, not {type(factory)!r}.")

    def register_providable_factory(self,
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
        if dependency in self.__builders:
            raise DuplicateDependencyError(dependency,
                                           self.__builders[dependency])

        with self.__freeze_lock:
            if self.__frozen:
                raise FrozenWorldError(f"Cannot add {dependency} to a frozen world.")
            self.__builders[dependency] = Builder(singleton=singleton,
                                                  takes_dependency=takes_dependency,
                                                  factory_dependency=factory_dependency)

cdef class Builder:
    """
    Not part of the public API.

    Only used by the FactoryProvider to store information on how the factory
    has to be used.
    """
    cdef:
        int flags
        bint takes_dependency
        object factory
        object factory_dependency

    def __init__(self,
                 bint singleton,
                 bint takes_dependency,
                 factory: Optional[Callable] = None,
                 factory_dependency: Optional[Hashable] = None):
        assert factory is not None or factory_dependency is not None
        self.flags = FLAG_SINGLETON if singleton else 0
        self.takes_dependency = takes_dependency
        self.factory = factory
        self.factory_dependency = factory_dependency

    def __repr__(self):
        return ("{}(singleton={!r}, takes_dependency={!r}, factory={!r},"
                "factory_dependency={!r})").format(
            type(self).__name__,
            self.flags == FLAG_SINGLETON,
            self.takes_dependency,
            self.factory,
            self.factory_dependency)
