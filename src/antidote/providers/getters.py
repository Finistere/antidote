from typing import Any, Callable, List, Optional

from .._internal.utils import SlotReprMixin
from ..container import Dependency, Instance, Provider
from ..exceptions import GetterNamespaceConflict


class GetterProvider(Provider):
    """
    Provider managing constant parameters like configuration.
    """

    def __init__(self):
        self._dependency_getters = []  # type: List[DependencyGetter]

    def __repr__(self):
        return "{}(getters={!r})".format(type(self).__name__, self._dependency_getters)

    def provide(self, dependency: Dependency) -> Optional[Instance]:
        """
        Provide the parameter associated with the dependency_id.

        Args:
            dependency: dependency to provide.

        Returns:
            A :py:class:`~.container.Instance` wrapping the built instance for
            the dependency.
        """
        if isinstance(dependency.id, str):
            for getter in self._dependency_getters:
                if dependency.id.startswith(getter.namespace_):
                    try:
                        instance = getter.get(dependency.id)
                    except LookupError:
                        break
                    else:
                        return Instance(instance, singleton=getter.singleton)

        return None

    def register(self,
                 getter: Callable[[str], Any],
                 namespace: str,
                 omit_namespace: bool = False,
                 singleton: bool = True):
        """
        Register parameters with its getter.

        Args:
            getter: Function used to retrieve a requested dependency which will
                be given as an argument. If the dependency cannot be provided,
                it should raise a :py:exc:`LookupError`.
            namespace: Used to identity which getter should be used with a
                dependency, as such they have to be mutually exclusive.
            omit_namespace: Whether or the namespace should be removed from the
                dependency name which is given to the getter. Defaults to False.

        """
        if not isinstance(namespace, str):
            raise ValueError("prefix must be a string")

        for g in self._dependency_getters:
            if g.namespace_.startswith(namespace) or namespace.startswith(g.namespace_):
                raise GetterNamespaceConflict(g.namespace_, namespace)

        self._dependency_getters.append(DependencyGetter(getter=getter,
                                                         namespace=namespace,
                                                         omit_namespace=omit_namespace,
                                                         singleton=singleton))


class DependencyGetter(SlotReprMixin):
    __slots__ = ('_getter', '_omit_namespace', 'namespace_', 'singleton')

    def __init__(self,
                 getter: Callable[[str], Any],
                 namespace: str,
                 omit_namespace: bool,
                 singleton: bool):
        self._getter = getter
        self._omit_namespace = omit_namespace
        self.namespace_ = namespace
        self.singleton = singleton

    def get(self, name):
        if self._omit_namespace:
            name = name[len(self.namespace_):]
        return self._getter(name)
