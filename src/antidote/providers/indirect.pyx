# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False
from enum import Enum
from typing import Any, Dict

# @formatter:off
from cpython.dict cimport PyDict_GetItem
from cpython.object cimport PyObject

from antidote.core.container cimport DependencyInstance, DependencyProvider
from ..exceptions import DuplicateDependencyError, UndefinedContextError
# @formatter:on


cdef class IndirectProvider(DependencyProvider):
    def __init__(self, container):
        super(IndirectProvider, self).__init__(container)
        self._contextual_links = dict()  # type: Dict[Any, ContextualLink]
        self._links = dict()  # type: Dict[Any, Any]

    cpdef DependencyInstance provide(self, object dependency):
        cdef:
            PyObject*ptr
            object service
            ContextualLink contextual_link
            DependencyInstance current_context
            DependencyInstance ContextualTarget_dependency

        ptr = PyDict_GetItem(self._links, dependency)
        if ptr != NULL:
            return self._container.safe_provide(<object> ptr)

        ptr = PyDict_GetItem(self._contextual_links, dependency)
        if ptr != NULL:
            contextual_link = <ContextualLink> ptr
            current_context = self._container.safe_provide(
                contextual_link.context_dependency
            )

            ptr = PyDict_GetItem(contextual_link.targets, current_context.instance)
            if ptr == NULL:
                raise UndefinedContextError(dependency, current_context.instance)

            target = self._container.safe_provide(<object> ptr)
            return DependencyInstance.__new__(
                DependencyInstance,
                target.instance,
                current_context.singleton & target.singleton
            )

        return None

    def register(self, dependency: Any, target_dependency: Any, context: Enum = None):
        cdef:
            ContextualLink contextual_link

        if dependency in self._links:
            raise DuplicateDependencyError(dependency,
                                           self._links[dependency])

        if context is None:
            if dependency in self._contextual_links:
                raise DuplicateDependencyError(dependency,
                                               self._contextual_links[dependency])
            self._links[dependency] = target_dependency
        elif isinstance(context, Enum):
            try:
                contextual_link = self._contextual_links[dependency]
            except KeyError:
                contextual_link = ContextualLink(type(context))
                self._contextual_links[dependency] = contextual_link

            if context in contextual_link.targets:
                raise DuplicateDependencyError((dependency, context),
                                               contextual_link.targets[context])

            contextual_link.targets[context] = target_dependency
        else:
            raise TypeError("profile must be an instance of Flag or be None, "
                            "not a {!r}".format(type(context)))

cdef class ContextualLink:
    cdef:
        object context_dependency
        dict targets

    def __init__(self, context_dependency):
        self.context_dependency = context_dependency
        self.targets = dict()  # type: Dict[Enum, Any]

    def __repr__(self):
        return "{}(context_dependency={!r}, targets={!r})".format(
            type(self).__name__,
            self.context_dependency,
            self.targets
        )
