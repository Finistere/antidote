import bisect
import re
from typing import Any, Callable, Dict, List, Optional

from .._internal.utils import SlotsReprMixin
from ..core import DependencyContainer, DependencyInstance, DependencyProvider
from ..exceptions import ResourcePriorityConflict


class ResourceProvider(DependencyProvider):
    """
    Provider managing resources, such as configuration, remote static content,
    etc...
    """

    def __init__(self, container: DependencyContainer):
        super().__init__(container)
        self._priority_sorted_resources_by_namespace = dict()  # type: Dict[str, List[Resource]]  # noqa

    def __repr__(self):
        return "{}(getters={!r})".format(type(self).__name__,
                                         self._priority_sorted_resources_by_namespace)

    def provide(self, dependency) -> Optional[DependencyInstance]:
        """

        Args:
            dependency:

        Returns:

        """
        if isinstance(dependency, str) and ':' in dependency:
            namespace, resource_name = dependency.split(':', 1)
            resources = self._priority_sorted_resources_by_namespace.get(namespace)
            if resources is not None:
                for resource in resources:
                    try:
                        instance = resource.getter(resource_name)
                    except LookupError:
                        pass
                    else:
                        return DependencyInstance(instance, singleton=True)

        return None

    def register(self,
                 getter: Callable[[str], Any],
                 namespace: str,
                 priority: float = 0):
        """
        Register a function used to retrieve a certain kind of resource.
        Resources must each have their own namespace which must be specified
        upon retrieval, like :code:`'<NAMESPACE>:<RESOURCE NAME>'`.

        Args:
            getter: Function used to retrieve a requested dependency
                which will be given as an argument. If the dependency cannot
                be provided,  it should raise a :py:exc:`LookupError`.
            namespace: Used to identity which getter should be used with a
                dependency. It should only contain characters in
                :code:`[a-zA-Z0-9_]`.
            priority: Used to determine which getter should be called first
                when they share the same namespace. Highest priority wins.
                Defaults to 0.

        """
        if not isinstance(namespace, str):
            raise TypeError(
                "namespace must be a string, not a {!r}".format(type(namespace))
            )
        elif not re.match(r'^\w+$', namespace):
            raise ValueError("namespace can only contain characters in [a-zA-Z0-9_]")

        if not isinstance(priority, (int, float)):
            raise TypeError(
                "priority must be a number, not a {!r}".format(type(priority))
            )

        if callable(getter):
            resource = Resource(getter=getter,
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


class Resource(SlotsReprMixin):
    """
    Not part of the public API.

    Only used by the GetterProvider to store information on how a getter has to
    be used.
    """
    __slots__ = ('getter', 'namespace_', 'priority')

    def __init__(self,
                 getter: Callable[[str], Any],
                 namespace: str,
                 priority: float):
        self.getter = getter
        self.namespace_ = namespace
        self.priority = priority
