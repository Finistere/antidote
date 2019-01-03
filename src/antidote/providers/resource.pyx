# cython: language_level=3, language=c++
# cython: boundscheck=False, wraparound=False
import bisect
import re
from typing import Any, Callable, Dict, List, Union, Optional

# @formatter:off
from cpython.dict cimport PyDict_GetItem
from cpython.ref cimport PyObject

from antidote.core import Lazy
from antidote.core.container cimport (DependencyContainer, DependencyInstance,
                                      DependencyProvider, Lazy)
from antidote.core.exceptions import DependencyNotFoundError
from ..exceptions import ResourcePriorityConflict
# @formatter:on


cdef class ResourceProvider(DependencyProvider):
    def __init__(self, DependencyContainer container):
        super().__init__(container)
        self._priority_sorted_resources_by_namespace = dict()  # type: Dict[str, List[Resource]]  # noqa

    def __repr__(self):
        return "{}(getters={!r})".format(type(self).__name__,
                                         self._priority_sorted_resources_by_namespace)

    cpdef DependencyInstance provide(self, object dependency):
        cdef:
            object instance
            object dependency_instance
            Resource resource
            str namespace_
            str resource_name
            str resource_full_name
            PyObject*ptr
            ssize_t i

        if isinstance(dependency, str):
            resource_full_name = <str> dependency
            i = resource_full_name.find(':')
            if i == -1:
                return
            else:
                namespace_ = resource_full_name[:i]
                resource_name = resource_full_name[i + 1:]
            ptr = PyDict_GetItem(self._priority_sorted_resources_by_namespace, namespace_)
            if ptr != NULL:
                for resource in <list> ptr:
                    if resource.lazy_dependency is not None:
                        dependency_instance = self._container.provide(resource.lazy_dependency)
                        if dependency_instance is None:
                            raise DependencyNotFoundError(dependency_instance)
                        resource.getter = dependency_instance
                        resource.lazy_dependency = None
                    try:
                        instance = resource.getter(resource_name)
                    except LookupError:
                        pass
                    else:
                        return DependencyInstance.__new__(DependencyInstance,
                                                          instance,
                                                          True)

    def register(self,
                 getter: Union[Callable[[str], Any], Lazy],
                 str namespace,
                 float priority = 0):
        cdef:
            list resources
            Resource r
            Resource resource
            int idx

        if not re.match(r'^\w+$', namespace):
            raise ValueError("namespace can only contain characters in [a-zA-Z0-9_]")

        if isinstance(getter, Lazy):
            resource = Resource(getter=None,
                                lazy_dependency=getter.dependency,
                                namespace=namespace,
                                priority=priority)
        elif callable(getter):
            resource = Resource(getter=getter,
                                lazy_dependency=None,
                                namespace=namespace,
                                priority=priority)
        else:
            raise ValueError("getter must be callable")

        resources = self._priority_sorted_resources_by_namespace.get(namespace) or []
        for r in resources:
            if r.priority == priority:
                raise ResourcePriorityConflict(repr(r.getter), repr(getter))

        # Highest priority should be first
        idx = bisect.bisect([-r.priority for r in resources], -priority)
        resources.insert(idx, resource)

        self._priority_sorted_resources_by_namespace[namespace] = resources


cdef class Resource:
    cdef:
        readonly object getter
        readonly object lazy_dependency
        readonly float priority
        readonly str namespace_

    def __init__(self,
                 getter: Optional[Callable[[str], Any]],
                 lazy_dependency: Optional[Any],
                 str namespace,
                 float priority):
        assert getter is not None or lazy_dependency is not None
        self.getter = getter
        self.lazy_dependency = lazy_dependency
        self.namespace_ = namespace
        self.priority = priority

    def __repr__(self):
        return "{}(getter={!r}, priority={!r}, namespace={!r}, " \
               "lazy_dependency={!r})".format(
            type(self).__name__,
            self.getter,
            self.priority,
            self.namespace_,
            self.lazy_dependency,
        )
