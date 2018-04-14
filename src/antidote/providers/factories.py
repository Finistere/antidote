from typing import Callable, Dict

from ..container import Dependency
from ..exceptions import (
    DependencyDuplicateError, DependencyNotProvidableError
)


class FactoryProvider:
    """
    Provider managing factories. When a dependency is requested, it tries
    to find a matching factory and builds it. Subclasses may also be built.
    """

    def __init__(self, auto_wire: bool = True) -> None:
        self.auto_wire = auto_wire
        self._factories = dict()  # type: Dict
        self._subclass_factories = dict()  # type: Dict

    def __repr__(self):
        return (
            "{}(auto_wire={!r}, factories={!r}, subclass_factories={!r}"
        ).format(
            type(self).__name__,
            self.auto_wire,
            tuple(self._factories.keys()),
            tuple(self._subclass_factories.keys())
        )

    def __antidote_provide__(self, dependency_id, *args,
                             **kwargs) -> Dependency:
        """
        Builds the dependency if a factory associated with the dependency_id
        can be found.

        Args:
            dependency_id: ID of the dependency.
            *args: passed on to the factory.
            **kwargs: passed on to the factory.

        Returns:
            A :py:class:`~.container.Dependency` wrapping the built dependency.
        """
        try:
            factory = self._factories[dependency_id]
        except KeyError:
            for cls in getattr(dependency_id, '__mro__', []):
                try:
                    factory = self._subclass_factories[cls]
                    break
                except KeyError:
                    pass
            else:
                raise DependencyNotProvidableError(dependency_id)

        if factory.takes_dependency_id:
            args = (dependency_id,) + args

        return Dependency(
            factory(*args, **kwargs),
            singleton=factory.singleton
        )

    def register(self,
                 dependency_id,
                 factory: Callable,
                 singleton: bool = True,
                 build_subclasses: bool = False):
        """
        Register a factory for a dependency.

        Args:
            dependency_id: ID of the dependency.
            factory: Callable used to instantiate the dependency.
            singleton: Whether the dependency should be mark as singleton or
                not for the :py:class:`~..container.DependencyContainer`.
            build_subclasses: If True, subclasses will also be build with this
                factory. If multiple factories are defined, the first in the
                MRO is used.
        """
        if not callable(factory):
            raise ValueError("The `factory` must be callable.")

        if not dependency_id:
            raise ValueError("`dependency_id` parameter must be specified.")

        dependency_factory = DependencyFactory(
            factory=factory,
            singleton=singleton,
            takes_dependency_id=build_subclasses,
        )

        if dependency_id in self._factories:
            raise DependencyDuplicateError(dependency_id)

        if build_subclasses:
            self._subclass_factories[dependency_id] = dependency_factory

        self._factories[dependency_id] = dependency_factory


class DependencyFactory(object):
    """
    Only used by the FactoryProvider, not part of the public API.

    Simple container to store information on how the factory has to be used.
    """
    __slots__ = ('factory', 'singleton', 'takes_dependency_id')

    def __init__(self,
                 factory,
                 singleton: bool,
                 takes_dependency_id: bool
                 ) -> None:
        self.factory = factory
        self.singleton = singleton
        self.takes_dependency_id = takes_dependency_id

    def __repr__(self):
        return (
            "{}(factory={!r}, singleton={!r}, takes_dependency_id={!r})"
        ).format(
            type(self).__name__,
            self.factory,
            self.singleton,
            self.takes_dependency_id
        )

    def __call__(self, *args, **kwargs):
        return self.factory(*args, **kwargs)
