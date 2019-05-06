# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False
from typing import Any, Callable, Dict, Hashable, Optional

# @formatter:off
from cpython.dict cimport PyDict_GetItem
from cpython.ref cimport PyObject

from antidote.core.container cimport (DependencyContainer, DependencyInstance,
                                     DependencyProvider)
from ..exceptions import DuplicateDependencyError
# @formatter:on


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

cdef class FactoryProvider(DependencyProvider):
    """
    Provider managing factories. Also used to register classes directly.
    """
    bound_dependency_types = (Build,)

    def __init__(self, DependencyContainer container):
        super().__init__(container)
        self._builders = dict()  # type: Dict[Any, Builder]

    def __repr__(self):
        return "{}(factories={!r})".format(type(self).__name__,
                                           tuple(self._builders.keys()))

    cpdef DependencyInstance provide(self, object dependency: Hashable):
        cdef:
            Builder builder
            Build build
            PyObject*ptr
            DependencyInstance f
            object instance
            object factory

        if isinstance(dependency, Build):
            build = <Build> dependency
            ptr = PyDict_GetItem(self._builders, build.dependency)
        else:
            ptr = PyDict_GetItem(self._builders, dependency)

        if ptr == NULL:
            return None

        builder = <Builder> ptr

        if builder.factory_dependency is not None:
            f = self._container.safe_provide(builder.factory_dependency)
            if f.singleton:
                builder.factory_dependency = None
                builder.factory = f.instance
            factory = f.instance
        else:
            factory = builder.factory

        if isinstance(dependency, Build):
            if builder.takes_dependency:
                instance = factory(build.dependency, **build.kwargs)
            else:
                instance = factory(**build.kwargs)
        else:
            if builder.takes_dependency:
                instance = factory(dependency)
            else:
                instance = factory()

        return DependencyInstance.__new__(DependencyInstance,
                                          instance,
                                          builder.singleton)

    def register_class(self, class_: type, singleton: bool = True):
        """
        Register a class which is both dependency and factory.

        Args:
            class_: dependency to register.
            singleton: Whether the dependency should be mark as singleton or
                not for the :py:class:`~..core.DependencyContainer`.
        """
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
        if dependency in self._builders:
            raise DuplicateDependencyError(dependency,
                                           self._builders[dependency])

        if callable(factory):
            self._builders[dependency] = Builder(singleton=singleton,
                                                 takes_dependency=takes_dependency,
                                                 factory=factory)
        else:
            raise TypeError("factory must be callable, not {!r}.".format(type(factory)))

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
        if dependency in self._builders:
            raise DuplicateDependencyError(dependency,
                                           self._builders[dependency])

        self._builders[dependency] = Builder(singleton=singleton,
                                             takes_dependency=takes_dependency,
                                             factory_dependency=factory_dependency)

cdef class Builder:
    """
    Not part of the public API.

    Only used by the FactoryProvider to store information on how the factory
    has to be used.
    """
    cdef:
        bint singleton
        bint takes_dependency
        object factory
        object factory_dependency

    def __init__(self,
                 bint singleton,
                 bint takes_dependency,
                 factory: Optional[Callable] = None,
                 factory_dependency: Optional[Hashable] = None):
        assert factory is not None or factory_dependency is not None
        self.singleton = singleton
        self.takes_dependency = takes_dependency
        self.factory = factory
        self.factory_dependency = factory_dependency

    def __repr__(self):
        return ("{}(singleton={!r}, takes_dependency={!r}, factory={!r},"
                "factory_dependency={!r})").format(
            type(self).__name__,
            self.singleton,
            self.takes_dependency,
            self.factory,
            self.factory_dependency)
