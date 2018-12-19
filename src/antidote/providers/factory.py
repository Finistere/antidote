from typing import Any, Callable, Dict, Optional, Tuple

from .._internal.utils import SlotReprMixin
from ..container import Dependency, Instance, Provider
from ..exceptions import DuplicateDependencyError


class FactoryProvider(Provider):
    """
    Provider managing factories. When a dependency is requested, it tries
    to find a matching factory and builds it. Subclasses may also be built.
    """

    def __init__(self):
        self._factories = dict()  # type: Dict[Any, DependencyFactory]

    def __repr__(self):
        return (
            "{}(factories={!r})"
        ).format(
            type(self).__name__,
            tuple(self._factories.keys()),
        )

    def provide(self, dependency: Dependency) -> Optional[Instance]:
        """
        Builds the dependency if a factory associated with the dependency_id
        can be found.

        Args:
            dependency: dependency to provide.

        Returns:
            A :py:class:`~.container.Instance` wrapping the built instance for
            the dependency.
        """

        try:
            factory = self._factories[dependency.id]  # type: DependencyFactory
        except KeyError:
            return None

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
        """
        Register a factory for a dependency.

        Args:
            dependency_id: ID of the dependency.
            factory: Callable used to instantiate the dependency.
            singleton: Whether the dependency should be mark as singleton or
                not for the :py:class:`~..container.DependencyContainer`.
            takes_dependency_id: If True, subclasses will also be build with this
                factory. If multiple factories are defined, the first in the
                MRO is used.
        """
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


class DependencyFactory(SlotReprMixin):
    """
    Only used by the FactoryProvider, not part of the public API.

    Simple container to store information on how the factory has to be used.
    """
    __slots__ = ('factory', 'singleton', 'takes_dependency_id')

    def __init__(self, factory: Callable, singleton: bool, takes_dependency_id: bool):
        self.factory = factory
        self.singleton = singleton
        self.takes_dependency_id = takes_dependency_id

    def __call__(self, *args, **kwargs):
        return self.factory(*args, **kwargs)


class Build(Dependency):
    __slots__ = ('args', 'kwargs')

    def __init__(self, *args, **kwargs):
        super().__init__(args[0])
        self.args = args[1:]  # type: Tuple
        self.kwargs = kwargs  # type: Dict

    def __hash__(self):
        if self.args or self.kwargs:
            try:
                # Try most precise hash first
                return hash((self.id, self.args, tuple(self.kwargs.items())))
            except TypeError:
                # If type error, return the best error-free hash possible
                return hash((self.id, len(self.args), tuple(self.kwargs.keys())))

        return hash(self.id)

    def __eq__(self, other):
        return ((not self.kwargs and not self.args
                 and (self.id is other or self.id == other))
                or (isinstance(other, Build)
                    and (self.id is other.id or self.id == other.id)
                    and self.args == other.args
                    and self.kwargs == other.kwargs))
