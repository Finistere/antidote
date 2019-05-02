# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False
from enum import Enum
from typing import Hashable, Dict

# @formatter:off
from cpython.dict cimport PyDict_GetItem
from cpython.object cimport PyObject

from antidote.core.container cimport DependencyInstance, DependencyProvider
from ..exceptions import DuplicateDependencyError, UndefinedContextError
# @formatter:on


cdef class IndirectProvider(DependencyProvider):
    def __init__(self, container):
        super(IndirectProvider, self).__init__(container)
        self._stateful_links = dict()  # type: Dict[Hashable, StatefulLink]
        self._links = dict()  # type: Dict[Hashable, Hashable]

    cpdef DependencyInstance provide(self, object dependency):
        cdef:
            PyObject*ptr
            object service
            StatefulLink stateful_link
            DependencyInstance state
            DependencyInstance ContextualTarget_dependency

        ptr = PyDict_GetItem(self._links, dependency)
        if ptr != NULL:
            return self._container.safe_provide(<object> ptr)

        ptr = PyDict_GetItem(self._stateful_links, dependency)
        if ptr != NULL:
            stateful_link = <StatefulLink> ptr
            state = self._container.safe_provide(
                stateful_link.state_dependency
            )

            ptr = PyDict_GetItem(stateful_link.targets, state.instance)
            if ptr == NULL:
                raise UndefinedContextError(dependency, state.instance)

            target = self._container.safe_provide(<object> ptr)
            return DependencyInstance.__new__(
                DependencyInstance,
                target.instance,
                state.singleton & target.singleton
            )

        return None

    def register(self, dependency: Hashable, target_dependency: Hashable, state: Enum = None):
        cdef:
            StatefulLink stateful_link

        if dependency in self._links:
            raise DuplicateDependencyError(dependency,
                                           self._links[dependency])

        if state is None:
            if dependency in self._stateful_links:
                raise DuplicateDependencyError(dependency,
                                               self._stateful_links[dependency])
            self._links[dependency] = target_dependency
        elif isinstance(state, Enum):
            try:
                stateful_link = self._stateful_links[dependency]
            except KeyError:
                stateful_link = StatefulLink(type(state))
                self._stateful_links[dependency] = stateful_link

            if state in stateful_link.targets:
                raise DuplicateDependencyError((dependency, state),
                                               stateful_link.targets[state])

            stateful_link.targets[state] = target_dependency
        else:
            raise TypeError("profile must be an instance of Flag or be None, "
                            "not a {!r}".format(type(state)))

cdef class StatefulLink:
    cdef:
        object state_dependency
        dict targets

    def __init__(self, state_dependency):
        self.state_dependency = state_dependency
        self.targets = dict()  # type: Dict[Enum, Hashable]

    def __repr__(self):
        return "{}(state_dependency={!r}, targets={!r})".format(
            type(self).__name__,
            self.state_dependency,
            self.targets
        )
