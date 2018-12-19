# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
# cython: linetrace=True
from typing import Any, Callable, List

# @formatter:off
from libcpp cimport bool as cbool

# noinspection PyUnresolvedReferences
from ..container cimport Dependency, Instance, Provider
from ..exceptions import GetterNamespaceConflict
# @formatter:on


cdef class GetterProvider(Provider):
    def __init__(self):
        self._dependency_getters = []  # type: List[DependencyGetter]

    def __repr__(self):
        return "{}(getters={!r})".format(type(self).__name__, self._dependency_getters)

    cpdef Instance provide(self, Dependency dependency):
        cdef:
            DependencyGetter getter
            object instance

        if isinstance(dependency.id, str):
            for getter in self._dependency_getters:
                if dependency.id.startswith(getter.namespace_):
                    try:
                        instance = getter.get(dependency.id)
                    except LookupError:
                        break
                    else:
                        return Instance(instance, singleton=getter.singleton)

    def register(self,
                 getter: Callable[[str], Any],
                 namespace: str,
                 omit_namespace: bool = False,
                 singleton: bool = True):
        if not isinstance(namespace, str):
            raise ValueError("prefix must be a string")

        for g in self._dependency_getters:
            if g.namespace_.startswith(namespace) or namespace.startswith(g.namespace_):
                raise GetterNamespaceConflict(g.namespace_, namespace)

        self._dependency_getters.append(DependencyGetter(getter=getter,
                                                         namespace=namespace,
                                                         omit_namespace=omit_namespace,
                                                         singleton=singleton))

cdef class DependencyGetter:
    cdef:
        public str namespace_
        public object singleton
        readonly object _getter
        readonly cbool _omit_namespace

    def __repr__(self):
        return "{}(getter={!r}, namespace={!r}, omit_namespace={!r}, " \
               "singleton={!r})".format(
            type(self).__name__,
            self._getter,
            self.namespace_,
            self._omit_namespace,
            self.singleton
        )

    def __init__(self,
                 getter: Callable[[str], Any],
                 namespace: str,
                 omit_namespace: bool,
                 singleton: bool):
        self._getter = getter
        self._omit_namespace = omit_namespace
        self.namespace_ = namespace
        self.singleton = singleton

    cdef object get(self, str name):
        if self._omit_namespace:
            name = name[len(self.namespace_):]
        return self._getter(name)
