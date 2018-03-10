from typing import Any, Callable, Dict

from ..container import Dependency
from ..exceptions import (
    DependencyDuplicateError, DependencyNotProvidableError
)


class FactoryProvider(object):
    def __init__(self, auto_wire=True):
        # type: (bool) -> None
        self.auto_wire = auto_wire
        self._factories = dict()  # type: Dict
        self._subclass_factories = dict()  # type: Dict

    def __antidote_provide__(self, dependency_id, *args, **kwargs):
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

    def register(self, dependency_id, factory, singleton=True,
                 build_subclasses=False):
        # type: (Any, Callable, bool, bool) -> None
        """Register a dependency factory by the type of the dependency.

        The dependency can either be registered with an id (the type of the
        dependency if not specified) or a hook.

        Args:
            factory (callable): Callable to be used to instantiate the
                dependency.
            dependency_id (object, optional): Id of the dependency, by which it
                is identified. Defaults to the type of the factory.
            singleton (bool, optional): A singleton will be only be
                instantiated once. Otherwise the dependency will instantiated
                anew every time.
            build_subclasses (bool, optional): If True, subclasses will also
                be build with this factory. If multiple factories are defined,
                the first in the MRO is used. Defaults to False.
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
    Simple container to store information on how the factory has to be used.
    """
    __slots__ = ('factory', 'singleton', 'takes_dependency_id')

    def __init__(self, factory, singleton, takes_dependency_id):
        # type: (Callable, bool, bool) -> None
        self.factory = factory
        self.singleton = singleton
        self.takes_dependency_id = takes_dependency_id

    def __call__(self, *args, **kwargs):
        return self.factory(*args, **kwargs)
