# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
# cython: linetrace=True
from typing import Any, Callable, Dict, Tuple

# @formatter:off
from libcpp cimport bool as cbool

# noinspection PyUnresolvedReferences
from ..container cimport Dependency, Instance, Provider
from ..exceptions import DuplicateDependencyError
# @formatter:on


cdef class FactoryProvider(Provider):
    def __init__(self):
        self._factories = dict()  # type: Dict[Any, DependencyFactory]

    def __repr__(self):
        return (
            "{}(factories={!r})"
        ).format(
            type(self).__name__,
            tuple(self._factories.keys()),
        )

    cpdef Instance provide(self, dependency: Dependency):
        cdef:
            DependencyFactory factory
            tuple args
            dict kwargs

        try:
            factory = self._factories[dependency.id]
        except KeyError:
            return

        if isinstance(dependency, Build):
            args = dependency.args
            kwargs = dependency.kwargs
        else:
            args = tuple()
            kwargs = dict()

        if factory.takes_dependency_id:
            args = (dependency.id,) + args

        return Instance(factory(*args, **kwargs),
                        singleton=factory.singleton)

    def register(self,
                 dependency_id,
                 factory: Callable,
                 singleton: bool = True,
                 takes_dependency_id: bool = False):
        if not callable(factory):
            raise ValueError("The `factory` must be callable.")

        if dependency_id is None:
            raise ValueError("`dependency_id` parameter must be specified.")

        dependency_factory = DependencyFactory(factory=factory,
                                               singleton=singleton,
                                               takes_dependency_id=takes_dependency_id)

        if dependency_id in self._factories:
            raise DuplicateDependencyError(dependency_id)

        self._factories[dependency_id] = dependency_factory

cdef class DependencyFactory:
    cdef:
        readonly object factory
        readonly cbool singleton
        readonly cbool takes_dependency_id

    def __init__(self, factory: Callable, singleton: bool, takes_dependency_id: bool):
        self.factory = factory
        self.singleton = singleton
        self.takes_dependency_id = takes_dependency_id

    def __repr__(self):
        return "{}(factory={!r}, singleton={!r}, takes_dependency_id={!r})".format(
            type(self).__name__,
            self.factory,
            self.singleton,
            self.takes_dependency_id
        )

    def __call__(self, *args, **kwargs):
        return self.factory(*args, **kwargs)

cdef class Build(Dependency):
    def __init__(self, *args, **kwargs):
        super().__init__(args[0])
        self.args = args[1:]  # type: Tuple
        self.kwargs = kwargs  # type: Dict

    def __repr__(self):
        return "{}(id={!r}, args={!r}, kwargs={!r})".format(
            type(self).__name__,
            self.id,
            self.args,
            self.kwargs
        )

    def __hash__(self):
        if self.args or self.kwargs:
            try:
                # Try most precise hash first
                return hash((self.id, self.args, tuple(self.kwargs.items())))
            except TypeError:
                # If type error, return the best error-free hash possible
                return hash((self.id, len(self.args), tuple(self.kwargs.keys())))

        return hash(self.id)

    def __eq__(self, object other):
        return ((not self.kwargs and not self.args
                 and (self.id is other or self.id == other))
                or (isinstance(other, Build)
                    and (self.id is other.id or self.id == other.id)
                    and self.args == other.args
                    and self.kwargs == other.kwargs))
