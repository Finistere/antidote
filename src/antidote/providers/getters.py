from typing import Any, Callable, List

from .base import Provider
from ..container import Dependency, Instance
from ..exceptions import DependencyNotProvidableError, GetterNamespaceConflict


class GetterProvider(Provider):
    """
    Provider managing constant parameters like configuration.
    """

    def __init__(self):
        self._dependency_getters = []  # type: List[DependencyGetter]

    def __repr__(self):
        return "{}(getters={!r})".format(type(self).__name__, self._dependency_getters)

    def __antidote_provide__(self, dependency: Dependency) -> Instance:
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
                if dependency.id.startswith(getter.namespace):
                    try:
                        return Instance(getter(dependency.id), singleton=True)
                    except LookupError:
                        break

        raise DependencyNotProvidableError(dependency)

    def register(self,
                 getter: Callable[[str], Any],
                 namespace: str,
                 omit_namespace: bool = None):
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
        omit_namespace = omit_namespace if omit_namespace is not None else False
        if not isinstance(namespace, str):
            raise ValueError("prefix must be a string")

        for g in self._dependency_getters:
            if g.namespace.startswith(namespace) or namespace.startswith(g.namespace):
                raise GetterNamespaceConflict(g.namespace, namespace)

        self._dependency_getters.append(DependencyGetter(func=getter,
                                                         namespace=namespace,
                                                         omit_namespace=omit_namespace))


class DependencyGetter:
    __slots__ = ('namespace', 'func', 'omit_namespace')

    def __init__(self,
                 func: Callable[[str], Any],
                 namespace: str,
                 omit_namespace: bool):
        self.func = func
        self.namespace = namespace
        self.omit_namespace = omit_namespace

    def __call__(self, name):
        if self.omit_namespace:
            name = name[len(self.namespace):]
        return self.func(name)
