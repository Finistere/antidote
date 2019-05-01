# cython: language_level=3
# cython: boundscheck=False, wraparound=False, annotation_typing=False
from enum import Flag
from typing import Any, Dict, List

# @formatter:off
from cpython.dict cimport PyDict_GetItem
from cpython.object cimport PyObject

from antidote.core.container cimport DependencyInstance, DependencyProvider
from ..exceptions import DuplicateDependencyError, UndefinedContextError
# @formatter:on

cdef class ContextualTarget:
    cdef:
        object context
        object target_dependency

    def __init__(self, context: Flag, target_dependency: Any):
        self.context = context
        self.target_dependency = target_dependency

    def __repr__(self):
        return (f"ContextualTarget(context={self.context!r}, "
                f"target_dependency={self.target_dependency!r})")

cdef class ContextualLink:
    cdef:
        object context_dependency
        list targets

    def __init__(self, context_dependency):
        self.context_dependency = context_dependency
        self.targets = list()  # type: List[ContextualTarget]

    cdef object add(self, context: Flag, target_dependency: Any):
        self.targets.append(ContextualTarget(context, target_dependency))

    cdef object get(self, context: Flag):
        cdef:
            ContextualTarget target

        for target in self.targets:
            if context in target.context:
                return target.target_dependency

    def __repr__(self):
        return (f"{type(self).__name__}("
                f"context_dependency={self.context_dependency!r}, "
                f"ContextualLink={self.targets!r})")

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

            service = contextual_link.get(current_context.instance)
            if service is None:
                raise UndefinedContextError(dependency, current_context.instance)

            target = self._container.safe_provide(service)
            return DependencyInstance.__new__(
                DependencyInstance,
                target.instance,
                current_context.singleton & target.singleton
            )

        return None

    def register(self, dependency: Any, target_dependency: Any, context: Flag = None):
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
        elif isinstance(context, Flag):
            try:
                contextual_link = self._contextual_links[dependency]
            except KeyError:
                contextual_link = ContextualLink(type(context))
                self._contextual_links[dependency] = contextual_link

            existing_target = contextual_link.get(context)
            if existing_target is not None:
                raise DuplicateDependencyError((dependency, context), existing_target)

            contextual_link.add(context, target_dependency)
        else:
            raise TypeError(f"profile must be an instance of Flag or be None, "
                            f"not a {type(context)!r}")
