from ..exceptions import (
    DependencyDuplicateError, DependencyNotProvidableError
)
from ..container import Dependency


class DependencyFactories(object):
    def __init__(self, auto_wire=True):
        self.auto_wire = auto_wire
        self._factories = dict()
        self._subclass_factories = dict()

    def __antidote_provide__(self, dependency_id):
        """
        Retrieves the dependency from the cached dependencies. If none matches,
        the container tries to find a matching factory or a matching value in
        the added dependencies.
        """
        try:
            factory = self._factories[dependency_id]
        except KeyError:
            for cls in getattr(dependency_id, '__mro__', []):
                if cls in self._subclass_factories:
                    factory = self._subclass_factories[cls]
                    break
            else:
                raise DependencyNotProvidableError(dependency_id)

        return Dependency(
            factory(dependency_id)
            if factory.takes_dependency_id else
            factory(),
            singleton=factory.singleton
        )

    def register(self, dependency_id, factory, singleton=True,
                 build_subclasses=False):
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
    __slots__ = ('factory', 'singleton', 'takes_dependency_id')

    def __init__(self, factory, singleton, takes_dependency_id):
        self.factory = factory
        self.singleton = singleton
        self.takes_dependency_id = takes_dependency_id

    def __call__(self, *args, **kwargs):
        return self.factory(*args, **kwargs)
